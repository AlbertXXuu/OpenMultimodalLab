from __future__ import annotations

import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from openmultimodal_lab.adapters.errors import (
    AdapterDependencyError,
    AdapterInputError,
)
from openmultimodal_lab.adapters.qwen3_vl import (
    DEFAULT_MODEL_REVISION,
    Qwen3VLAdapter,
)
from openmultimodal_lab.adapters.transformers_image_text import (
    TransformersDependencies,
)
from openmultimodal_lab.models import EvaluationTask
from openmultimodal_lab.reporting import load_records
from openmultimodal_lab.runner import run_benchmark


class _FakeTokenRow(list[int]):
    @property
    def shape(self) -> tuple[int]:
        return (len(self),)


class _FakeInputIds:
    shape = (1, 3)


class _FakeInputs(dict[str, object]):
    def __init__(self) -> None:
        super().__init__(input_ids=_FakeInputIds())
        self.target_device: str | None = None

    def to(self, device: str) -> "_FakeInputs":
        self.target_device = device
        return self


class _FakeImage:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeImageSource:
    size = (16, 16)

    def __init__(self, converted: _FakeImage) -> None:
        self.converted = converted

    def __enter__(self) -> "_FakeImageSource":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def convert(self, mode: str) -> _FakeImage:
        if mode != "RGB":
            raise AssertionError(f"unexpected image mode: {mode}")
        return self.converted


class _FakeImageModule:
    def __init__(self) -> None:
        self.converted = _FakeImage()
        self.opened_path: Path | None = None

    def open(self, path: Path) -> _FakeImageSource:
        self.opened_path = path
        return _FakeImageSource(self.converted)


class _FakeVideo:
    shape = (8, 16, 16, 3)


class _FakeVideoMetadata:
    total_num_frames = 16
    fps = 8.0
    duration = 2.0
    width = 16
    height = 16


class _FakeNumpyArray(list[int]):
    def tolist(self) -> list[int]:
        return list(self)


def _fake_numpy_module() -> ModuleType:
    module = ModuleType("numpy")

    def asarray(values: object, *, dtype: type[int]) -> _FakeNumpyArray:
        return _FakeNumpyArray(dtype(value) for value in values)

    module.asarray = asarray  # type: ignore[attr-defined]
    return module


class _FakeVideoLoader:
    def __init__(self) -> None:
        self.call: tuple[str, dict[str, object]] | None = None
        self.video = _FakeVideo()
        self.metadata = _FakeVideoMetadata()
        self.sampled_indices: tuple[int, ...] = ()

    def __call__(self, path: str, **kwargs: object) -> tuple[_FakeVideo, object]:
        self.call = (path, kwargs)
        sampler = kwargs["sample_indices_fn"]
        self.sampled_indices = tuple(
            int(index) for index in sampler(self.metadata)
        )
        return self.video, self.metadata


class _FakeProcessor:
    class _Tokenizer:
        pad_token_id = 42

    def __init__(self) -> None:
        self.messages: object = None
        self.template_kwargs: dict[str, object] = {}
        self.inputs = _FakeInputs()
        self.tokenizer = self._Tokenizer()

    def apply_chat_template(self, messages: object, **kwargs: object) -> _FakeInputs:
        self.messages = messages
        self.template_kwargs = kwargs
        if kwargs["tokenize"] is not True:
            raise AssertionError("chat template should tokenize")
        return self.inputs

    def batch_decode(self, token_rows: object, **kwargs: object) -> list[str]:
        self.decoded_rows = token_rows
        return ["three purple circles"]


class _FakeProcessorLoader:
    processor = _FakeProcessor()
    call: tuple[str, dict[str, object]] | None = None

    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: object) -> _FakeProcessor:
        cls.call = (model_id, kwargs)
        return cls.processor


class _FakeModel:
    device = "cuda:0"
    dtype = "torch.float16"

    def __init__(self) -> None:
        self.generation_kwargs: dict[str, object] | None = None

    def eval(self) -> "_FakeModel":
        return self

    def generate(self, **kwargs: object) -> list[_FakeTokenRow]:
        self.generation_kwargs = kwargs
        for processor in kwargs["logits_processor"]:
            processor(None, None)
        return [_FakeTokenRow([1, 2, 3, 7, 8])]


class _OutOfMemoryModel(_FakeModel):
    def generate(self, **kwargs: object) -> list[_FakeTokenRow]:
        raise RuntimeError("CUDA out of memory while allocating tensor")


class _FakeModelLoader:
    model = _FakeModel()
    call: tuple[str, dict[str, object]] | None = None

    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: object) -> _FakeModel:
        cls.call = (model_id, kwargs)
        return cls.model


class _FakeTorch:
    @staticmethod
    def inference_mode() -> nullcontext[None]:
        return nullcontext()


class _FakeCuda:
    synchronized_devices: list[str] = []
    reset_devices: list[str] = []

    @staticmethod
    def is_available() -> bool:
        return True

    @classmethod
    def synchronize(cls, device: str) -> None:
        cls.synchronized_devices.append(device)

    @classmethod
    def reset_peak_memory_stats(cls, device: str) -> None:
        cls.reset_devices.append(device)

    @staticmethod
    def max_memory_allocated(device: str) -> int:
        return 4096 * 1024 * 1024


class _FakeCudaTorch(_FakeTorch):
    cuda = _FakeCuda


class Qwen3VLAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeProcessorLoader.processor = _FakeProcessor()
        _FakeProcessorLoader.call = None
        _FakeModelLoader.model = _FakeModel()
        _FakeModelLoader.call = None
        _FakeCuda.synchronized_devices = []
        _FakeCuda.reset_devices = []

    def test_generates_with_pinned_revision_and_records_configuration(self) -> None:
        image_module = _FakeImageModule()
        dependencies = TransformersDependencies(
            torch=_FakeTorch(),
            auto_model=_FakeModelLoader,
            auto_processor=_FakeProcessorLoader,
            image_module=image_module,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = root / "image.png"
            image.write_bytes(b"test image placeholder")
            task = EvaluationTask(
                id="counting-1",
                prompt="How many circles are there?",
                media=("image.png",),
            )
            adapter = Qwen3VLAdapter(media_root=root, max_new_tokens=16)

            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
                return_value=dependencies,
            ):
                output = adapter.generate(task, timeout_seconds=30)

        self.assertEqual(output.text, "three purple circles")
        self.assertEqual(output.backend, "qwen3-vl")
        self.assertEqual(output.model_revision, DEFAULT_MODEL_REVISION)
        self.assertEqual(output.usage["input_tokens"], 3)
        self.assertEqual(output.usage["output_tokens"], 2)
        self.assertEqual(
            output.usage["input_tensor_shapes"],
            {"input_ids": [1, 3]},
        )
        self.assertEqual(output.usage["max_new_tokens"], 16)
        self.assertIsInstance(output.usage["model_load_ms"], float)
        self.assertIsInstance(output.usage["media_load_ms"], float)
        self.assertIsInstance(output.usage["preprocessing_ms"], float)
        self.assertIsInstance(output.usage["ttft_ms"], float)
        self.assertIsInstance(output.usage["generation_ms"], float)
        self.assertIsInstance(output.usage["text_decode_ms"], float)
        self.assertIsInstance(
            output.usage["output_tokens_per_second"],
            float,
        )
        self.assertIsInstance(
            output.usage["decode_tokens_per_second"],
            float,
        )
        self.assertIsNone(output.usage["peak_gpu_memory_mb"])
        self.assertEqual(
            _FakeModelLoader.call[1]["revision"],
            DEFAULT_MODEL_REVISION,
        )
        self.assertEqual(
            _FakeProcessorLoader.call[1]["revision"],
            DEFAULT_MODEL_REVISION,
        )
        self.assertEqual(
            _FakeModelLoader.model.generation_kwargs["do_sample"],
            False,
        )
        self.assertEqual(
            _FakeModelLoader.model.generation_kwargs["pad_token_id"],
            42,
        )
        self.assertEqual(output.usage["pad_token_id"], 42)
        self.assertGreater(
            _FakeModelLoader.model.generation_kwargs["max_time"],
            0,
        )
        self.assertLessEqual(
            _FakeModelLoader.model.generation_kwargs["max_time"],
            30,
        )
        self.assertEqual(
            _FakeProcessorLoader.processor.inputs.target_device,
            "cuda:0",
        )
        self.assertTrue(image_module.converted.closed)

    def test_video_uses_bounded_uniform_frame_preprocessing(self) -> None:
        image_module = _FakeImageModule()
        video_loader = _FakeVideoLoader()
        dependencies = TransformersDependencies(
            torch=_FakeTorch(),
            auto_model=_FakeModelLoader,
            auto_processor=_FakeProcessorLoader,
            image_module=image_module,
            video_loader=video_loader,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = root / "clip.mp4"
            video.write_bytes(b"video placeholder handled by fake processor")
            task = EvaluationTask(
                id="event-order-1",
                prompt="What happens first?",
                media=("clip.mp4",),
            )
            adapter = Qwen3VLAdapter(
                media_root=root,
                max_new_tokens=16,
                video_num_frames=8,
            )

            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
                return_value=dependencies,
            ), patch.dict("sys.modules", {"numpy": _fake_numpy_module()}):
                output = adapter.generate(task)

        content = _FakeProcessorLoader.processor.messages[0]["content"]
        self.assertEqual(content[0]["type"], "video")
        self.assertIs(content[0]["video"], video_loader.video)
        self.assertEqual(
            content[1],
            {"type": "text", "text": "What happens first?"},
        )
        self.assertEqual(
            _FakeProcessorLoader.processor.template_kwargs["do_sample_frames"],
            False,
        )
        self.assertEqual(
            _FakeProcessorLoader.processor.template_kwargs["video_metadata"],
            [video_loader.metadata],
        )
        self.assertEqual(video_loader.call[0], str(video.resolve()))
        self.assertEqual(video_loader.call[1]["num_frames"], 8)
        self.assertEqual(video_loader.call[1]["backend"], "pyav")
        self.assertTrue(callable(video_loader.call[1]["sample_indices_fn"]))
        self.assertEqual(video_loader.sampled_indices, tuple(range(0, 16, 2)))
        self.assertIsNone(image_module.opened_path)
        self.assertEqual(output.usage["media_types"], ["video"])
        self.assertEqual(output.usage["image_count"], 0)
        self.assertEqual(output.usage["video_count"], 1)
        self.assertEqual(output.usage["video_num_frames"], 8)
        self.assertEqual(output.usage["video_frame_counts"], [8])
        self.assertEqual(
            output.usage["video_sampling"][0]["sampled_indices"],
            list(range(0, 16, 2)),
        )
        self.assertEqual(
            output.usage["video_sampling"][0]["dimensions"],
            [16, 16],
        )
        self.assertIsInstance(output.usage["video_decode_ms"], float)
        self.assertEqual(
            output.usage["media_limits"]["max_video_duration_seconds"],
            60.0,
        )

    def test_rejects_video_outside_short_input_limits(self) -> None:
        video_loader = _FakeVideoLoader()
        video_loader.metadata.total_num_frames = 3601
        dependencies = TransformersDependencies(
            torch=_FakeTorch(),
            auto_model=_FakeModelLoader,
            auto_processor=_FakeProcessorLoader,
            image_module=_FakeImageModule(),
            video_loader=video_loader,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "clip.mp4").write_bytes(b"video")
            task = EvaluationTask(
                id="long-video",
                prompt="Describe.",
                media=("clip.mp4",),
            )
            adapter = Qwen3VLAdapter(media_root=root)
            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
                return_value=dependencies,
            ):
                with self.assertRaisesRegex(
                    AdapterInputError,
                    "video frame count must be 1-3600",
                ):
                    adapter.generate(task)

    def test_fractional_video_sampling_remains_uniform(self) -> None:
        metadata = _FakeVideoMetadata()
        metadata.total_num_frames = 12
        adapter = Qwen3VLAdapter(video_num_frames=8)

        with patch.dict("sys.modules", {"numpy": _fake_numpy_module()}):
            indices = adapter._sample_video_indices(metadata).tolist()

        self.assertEqual(indices, [0, 1, 3, 4, 6, 7, 9, 10])

    def test_rejects_oversized_media_before_model_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = root / "oversized.mp4"
            video.write_bytes(b"x" * 1025)
            task = EvaluationTask(
                id="oversized-video",
                prompt="Describe.",
                media=("oversized.mp4",),
            )
            adapter = Qwen3VLAdapter(media_root=root)
            with patch(
                "openmultimodal_lab.adapters.transformers_image_text."
                "MAX_VIDEO_FILE_BYTES",
                1024,
            ), patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
            ) as dependency_loader:
                with self.assertRaisesRegex(
                    AdapterInputError,
                    "exceeds the .* safety limit",
                ):
                    adapter.generate(task)

        dependency_loader.assert_not_called()

    def test_rejects_unknown_visual_media_extension_before_model_load(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "media.bin").write_bytes(b"unknown")
            task = EvaluationTask(
                id="unknown-media",
                prompt="Describe.",
                media=("media.bin",),
            )
            adapter = Qwen3VLAdapter(media_root=root)
            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
            ) as dependency_loader:
                with self.assertRaisesRegex(
                    AdapterInputError,
                    "unsupported extension '.bin'",
                ):
                    adapter.generate(task)

        dependency_loader.assert_not_called()

    def test_cuda_timings_synchronize_and_record_peak_allocated_memory(
        self,
    ) -> None:
        dependencies = TransformersDependencies(
            torch=_FakeCudaTorch(),
            auto_model=_FakeModelLoader,
            auto_processor=_FakeProcessorLoader,
            image_module=_FakeImageModule(),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "image.png").write_bytes(b"test image placeholder")
            task = EvaluationTask(
                id="image-1",
                prompt="Describe.",
                media=("image.png",),
            )
            adapter = Qwen3VLAdapter(media_root=root)

            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
                return_value=dependencies,
            ):
                output = adapter.generate(task)

        self.assertGreaterEqual(len(_FakeCuda.synchronized_devices), 3)
        self.assertEqual(_FakeCuda.reset_devices, ["cuda:0"])
        self.assertEqual(output.usage["peak_gpu_memory_mb"], 4096)

    def test_missing_optional_dependencies_become_model_load_records(self) -> None:
        task = EvaluationTask(
            id="image-1",
            prompt="Describe the image.",
            media=("image.png",),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "image.png").write_bytes(b"test image placeholder")
            output = root / "run.jsonl"
            adapter = Qwen3VLAdapter(media_root=root)
            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
                side_effect=AdapterDependencyError("install optional packages"),
            ) as dependency_loader:
                run_benchmark(
                    [
                        task,
                        EvaluationTask(
                            id="image-2",
                            prompt="Describe another image.",
                            media=("image.png",),
                        ),
                    ],
                    adapter,
                    output,
                )
            records = load_records(output)

        self.assertEqual(
            [record["status"] for record in records],
            ["model_load_error", "model_load_error"],
        )
        self.assertTrue(
            all(
                record["model_revision"] == DEFAULT_MODEL_REVISION
                for record in records
            )
        )
        self.assertIn("install optional packages", records[0]["error"])
        dependency_loader.assert_called_once_with()

    def test_missing_media_is_rejected_before_loading_model(self) -> None:
        task = EvaluationTask(
            id="text-only",
            prompt="This backend requires an image.",
        )
        adapter = Qwen3VLAdapter()

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
            ) as dependency_loader:
                run_benchmark([task], adapter, output)
            record = load_records(output)[0]

        self.assertEqual(record["status"], "invalid_task")
        dependency_loader.assert_not_called()

    def test_cuda_out_of_memory_becomes_specific_record(self) -> None:
        image_module = _FakeImageModule()
        _FakeModelLoader.model = _OutOfMemoryModel()
        dependencies = TransformersDependencies(
            torch=_FakeTorch(),
            auto_model=_FakeModelLoader,
            auto_processor=_FakeProcessorLoader,
            image_module=image_module,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "image.png").write_bytes(b"test image placeholder")
            output = root / "run.jsonl"
            task = EvaluationTask(
                id="image-1",
                prompt="Describe the image.",
                media=("image.png",),
            )
            adapter = Qwen3VLAdapter(media_root=root)

            with patch(
                "openmultimodal_lab.adapters.qwen3_vl._load_dependencies",
                return_value=dependencies,
            ):
                run_benchmark([task], adapter, output)
            record = load_records(output)[0]

        self.assertEqual(record["status"], "out_of_memory")
        self.assertIn("CUDA out of memory", record["error"])


if __name__ == "__main__":
    unittest.main()

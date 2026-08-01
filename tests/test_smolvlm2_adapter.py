from __future__ import annotations

import tempfile
import unittest
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from openmultimodal_lab.adapters.factory import create_adapter
from openmultimodal_lab.adapters.smolvlm2 import (
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    SmolVLM2Adapter,
)
from openmultimodal_lab.adapters.transformers_image_text import (
    TransformersDependencies,
)
from openmultimodal_lab.models import EvaluationTask


class _Inputs(dict[str, object]):
    class _InputIds:
        shape = (1, 3)

    def __init__(self) -> None:
        super().__init__(input_ids=self._InputIds())
        self.device: str | None = None
        self.dtype: object = None

    def to(self, device: str, *, dtype: object = None) -> "_Inputs":
        self.device = device
        self.dtype = dtype
        return self


class _Image:
    def close(self) -> None:
        return None


class _ImageSource:
    size = (16, 16)

    def __enter__(self) -> "_ImageSource":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def convert(self, mode: str) -> _Image:
        if mode != "RGB":
            raise AssertionError(f"unexpected mode: {mode}")
        return _Image()


class _ImageModule:
    @staticmethod
    def open(path: Path) -> _ImageSource:
        return _ImageSource()


class _Video:
    shape = (8, 16, 16, 3)


class _VideoMetadata:
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


class _VideoLoader:
    def __init__(self) -> None:
        self.call: tuple[str, dict[str, object]] | None = None
        self.video = _Video()
        self.metadata = _VideoMetadata()
        self.sampled_indices: tuple[int, ...] = ()

    def __call__(self, path: str, **kwargs: object) -> tuple[_Video, object]:
        self.call = (path, kwargs)
        sampler = kwargs["sample_indices_fn"]
        self.sampled_indices = tuple(
            int(index) for index in sampler(self.metadata)
        )
        return self.video, self.metadata


class _Processor:
    class _Tokenizer:
        pad_token_id = 2

    @dataclass
    class _Size:
        longest_edge: int
        height: int | None = None

    class _ImageProcessor:
        do_resize = True
        size: object = None
        patch_size = 14

    def __init__(self) -> None:
        self.inputs = _Inputs()
        self.messages: object = None
        self.template_kwargs: dict[str, object] = {}
        self.processor_kwargs: dict[str, object] = {}
        self.image_processor = self._ImageProcessor()
        self.image_processor.size = self._Size(longest_edge=384)
        self.tokenizer = self._Tokenizer()

    def apply_chat_template(
        self,
        messages: object,
        *,
        processor_kwargs: dict[str, object] | None = None,
        **kwargs: object,
    ) -> _Inputs:
        self.messages = messages
        self.template_kwargs = kwargs
        self.processor_kwargs = processor_kwargs or {}
        return self.inputs

    @staticmethod
    def batch_decode(rows: object, **kwargs: object) -> list[str]:
        return ["2"]


class _ProcessorLoader:
    processor = _Processor()
    call: tuple[str, dict[str, object]] | None = None

    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: object) -> _Processor:
        cls.call = (model_id, kwargs)
        return cls.processor


class _TokenRow(list[int]):
    pass


class _Model:
    device = "cpu"
    dtype = "torch.float32"
    generation_kwargs: dict[str, object] | None = None

    def eval(self) -> "_Model":
        return self

    @classmethod
    def generate(cls, **kwargs: object) -> list[_TokenRow]:
        cls.generation_kwargs = kwargs
        for processor in kwargs["logits_processor"]:
            processor(None, None)
        return [_TokenRow([1, 2, 3, 7])]


class _ModelLoader:
    model = _Model()
    call: tuple[str, dict[str, object]] | None = None

    @classmethod
    def from_pretrained(cls, model_id: str, **kwargs: object) -> _Model:
        cls.call = (model_id, kwargs)
        return cls.model


class _Torch:
    bfloat16 = "torch.bfloat16"

    @staticmethod
    def inference_mode() -> nullcontext[None]:
        return nullcontext()


class SmolVLM2AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        _ProcessorLoader.processor = _Processor()
        _ProcessorLoader.call = None
        _ModelLoader.model = _Model()
        _Model.generation_kwargs = None
        _ModelLoader.call = None

    def test_factory_uses_pinned_official_checkpoint(self) -> None:
        adapter = create_adapter("smolvlm2")

        self.assertIsInstance(adapter, SmolVLM2Adapter)
        self.assertEqual(adapter.model_id, DEFAULT_MODEL_ID)
        self.assertEqual(adapter.revision, DEFAULT_MODEL_REVISION)

    def test_generate_uses_shared_performance_contract(self) -> None:
        dependencies = TransformersDependencies(
            torch=_Torch(),
            auto_model=_ModelLoader,
            auto_processor=_ProcessorLoader,
            image_module=_ImageModule(),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "image.png").write_bytes(b"placeholder")
            task = EvaluationTask(
                id="counting-1",
                prompt="How many shapes?",
                media=("image.png",),
            )
            adapter = SmolVLM2Adapter(media_root=root, max_new_tokens=8)
            with patch(
                "openmultimodal_lab.adapters.smolvlm2._load_dependencies",
                return_value=dependencies,
            ):
                output = adapter.generate(task)

        self.assertEqual(output.text, "2")
        self.assertEqual(output.backend, "smolvlm2")
        self.assertEqual(output.model_revision, DEFAULT_MODEL_REVISION)
        self.assertEqual(output.usage["pad_token_id"], 2)
        self.assertEqual(_Model.generation_kwargs["pad_token_id"], 2)
        self.assertEqual(
            _ModelLoader.call,
            (
                DEFAULT_MODEL_ID,
                {
                    "revision": DEFAULT_MODEL_REVISION,
                    "dtype": "torch.bfloat16",
                    "device_map": "auto",
                    "low_cpu_mem_usage": True,
                },
            ),
        )
        self.assertEqual(
            _ProcessorLoader.call,
            (DEFAULT_MODEL_ID, {"revision": DEFAULT_MODEL_REVISION}),
        )
        self.assertEqual(_ProcessorLoader.processor.inputs.device, "cpu")
        self.assertEqual(
            _ProcessorLoader.processor.inputs.dtype,
            "torch.bfloat16",
        )
        self.assertEqual(output.usage["input_tokens"], 3)
        self.assertEqual(output.usage["output_tokens"], 1)
        self.assertEqual(
            output.usage["input_tensor_shapes"],
            {"input_ids": [1, 3]},
        )
        self.assertEqual(output.usage["model_class"], "_Model")
        self.assertEqual(output.usage["processor_class"], "_Processor")
        self.assertEqual(
            output.usage["image_processor_size"],
            {"longest_edge": 384},
        )
        self.assertEqual(output.usage["image_processor_patch_size"], 14)
        self.assertEqual(
            output.usage["chat_template"],
            "processor.apply_chat_template",
        )
        for key in (
            "model_load_ms",
            "media_load_ms",
            "preprocessing_ms",
            "ttft_ms",
            "generation_ms",
            "text_decode_ms",
            "output_tokens_per_second",
        ):
            self.assertIsInstance(output.usage[key], float, key)

    def test_video_uses_the_same_bounded_frame_contract(self) -> None:
        video_loader = _VideoLoader()
        dependencies = TransformersDependencies(
            torch=_Torch(),
            auto_model=_ModelLoader,
            auto_processor=_ProcessorLoader,
            image_module=_ImageModule(),
            video_loader=video_loader,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = root / "clip.webm"
            video.write_bytes(b"video placeholder handled by fake processor")
            task = EvaluationTask(
                id="scene-change-1",
                prompt="What changes?",
                media=("clip.webm",),
            )
            adapter = SmolVLM2Adapter(
                media_root=root,
                video_num_frames=8,
            )
            with patch(
                "openmultimodal_lab.adapters.smolvlm2._load_dependencies",
                return_value=dependencies,
            ), patch.dict("sys.modules", {"numpy": _fake_numpy_module()}):
                output = adapter.generate(task)

        content = _ProcessorLoader.processor.messages[0]["content"]
        self.assertEqual(content[0]["type"], "video")
        self.assertIs(content[0]["video"], video_loader.video)
        self.assertEqual(
            content[1],
            {"type": "text", "text": "What changes?"},
        )
        self.assertEqual(
            _ProcessorLoader.processor.processor_kwargs["do_sample_frames"],
            False,
        )
        self.assertEqual(
            _ProcessorLoader.processor.processor_kwargs["video_metadata"],
            [video_loader.metadata],
        )
        self.assertNotIn(
            "do_sample_frames",
            _ProcessorLoader.processor.template_kwargs,
        )
        self.assertEqual(video_loader.call[0], str(video.resolve()))
        self.assertEqual(video_loader.call[1]["num_frames"], 8)
        self.assertEqual(video_loader.call[1]["backend"], "pyav")
        self.assertTrue(callable(video_loader.call[1]["sample_indices_fn"]))
        self.assertEqual(video_loader.sampled_indices, tuple(range(0, 16, 2)))
        self.assertEqual(output.usage["media_types"], ["video"])
        self.assertEqual(output.usage["video_count"], 1)
        self.assertEqual(output.usage["video_num_frames"], 8)
        self.assertEqual(output.usage["video_frame_counts"], [8])
        self.assertEqual(
            output.usage["video_sampling"][0]["sampled_indices"],
            list(range(0, 16, 2)),
        )


if __name__ == "__main__":
    unittest.main()

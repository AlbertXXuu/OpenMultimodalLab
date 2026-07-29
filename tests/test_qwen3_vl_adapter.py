from __future__ import annotations

import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from openmultimodal_lab.adapters.errors import AdapterDependencyError
from openmultimodal_lab.adapters.qwen3_vl import (
    DEFAULT_MODEL_REVISION,
    Qwen3VLAdapter,
    _Dependencies,
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


class _FakeProcessor:
    def __init__(self) -> None:
        self.messages: object = None
        self.inputs = _FakeInputs()

    def apply_chat_template(self, messages: object, **kwargs: object) -> _FakeInputs:
        self.messages = messages
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


class Qwen3VLAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeProcessorLoader.processor = _FakeProcessor()
        _FakeProcessorLoader.call = None
        _FakeModelLoader.model = _FakeModel()
        _FakeModelLoader.call = None

    def test_generates_with_pinned_revision_and_records_configuration(self) -> None:
        image_module = _FakeImageModule()
        dependencies = _Dependencies(
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
                output = adapter.generate(task)

        self.assertEqual(output.text, "three purple circles")
        self.assertEqual(output.backend, "qwen3-vl")
        self.assertEqual(output.model_revision, DEFAULT_MODEL_REVISION)
        self.assertEqual(output.usage["input_tokens"], 3)
        self.assertEqual(output.usage["output_tokens"], 2)
        self.assertEqual(output.usage["max_new_tokens"], 16)
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
            _FakeProcessorLoader.processor.inputs.target_device,
            "cuda:0",
        )
        self.assertTrue(image_module.converted.closed)

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
        dependencies = _Dependencies(
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

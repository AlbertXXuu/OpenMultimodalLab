from __future__ import annotations

import tempfile
import unittest
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
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


class _Processor:
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
        self.image_processor = self._ImageProcessor()
        self.image_processor.size = self._Size(longest_edge=384)

    def apply_chat_template(self, messages: object, **kwargs: object) -> _Inputs:
        self.messages = messages
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

    def eval(self) -> "_Model":
        return self

    @staticmethod
    def generate(**kwargs: object) -> list[_TokenRow]:
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


if __name__ == "__main__":
    unittest.main()

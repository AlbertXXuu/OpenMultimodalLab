"""Local Transformers adapter for Qwen3-VL instruction models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any

from ..models import EvaluationTask, ModelOutput
from .errors import (
    AdapterError,
    AdapterDependencyError,
    AdapterInputError,
    AdapterOutOfMemoryError,
    ModelLoadError,
)

DEFAULT_MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
DEFAULT_MODEL_REVISION = "89644892e4d85e24eaac8bacfd4f463576704203"


@dataclass(frozen=True, slots=True)
class _Dependencies:
    torch: Any
    auto_model: Any
    auto_processor: Any
    image_module: Any


class _FirstTokenTimer:
    """Transformers logits hook used to mark the first generated token."""

    def __init__(self, synchronize: Any) -> None:
        self._synchronize = synchronize
        self.first_token_ns: int | None = None

    def __call__(self, input_ids: Any, scores: Any) -> Any:
        if self.first_token_ns is None:
            self._synchronize()
            self.first_token_ns = perf_counter_ns()
        return scores


def _load_dependencies() -> _Dependencies:
    try:
        import torch
        from PIL import Image
        from transformers import AutoModelForImageTextToText, AutoProcessor
    except ImportError as exc:
        raise AdapterDependencyError(
            "Qwen3-VL dependencies are missing. Install the 'qwen3-vl' "
            "optional dependency group in a Python 3.11/3.12 environment."
        ) from exc

    return _Dependencies(
        torch=torch,
        auto_model=AutoModelForImageTextToText,
        auto_processor=AutoProcessor,
        image_module=Image,
    )


class Qwen3VLAdapter:
    """Run a pinned Qwen3-VL checkpoint locally through Transformers."""

    name = "qwen3-vl"

    def __init__(
        self,
        *,
        media_root: str | Path = ".",
        model_id: str = DEFAULT_MODEL_ID,
        revision: str = DEFAULT_MODEL_REVISION,
        max_new_tokens: int = 128,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must be non-empty")
        if not revision.strip():
            raise ValueError("revision must be non-empty")
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be at least 1")

        self.media_root = Path(media_root)
        self.model_id = model_id.strip()
        self.revision = revision.strip()
        self.max_new_tokens = max_new_tokens
        self._dependencies: _Dependencies | None = None
        self._model: Any = None
        self._processor: Any = None
        self._load_error: AdapterError | None = None

    def _ensure_loaded(self) -> float:
        if self._model is not None and self._processor is not None:
            return 0.0
        if self._load_error is not None:
            raise self._load_error

        load_start_ns = perf_counter_ns()
        try:
            dependencies = _load_dependencies()
            processor = dependencies.auto_processor.from_pretrained(
                self.model_id,
                revision=self.revision,
            )
            model = dependencies.auto_model.from_pretrained(
                self.model_id,
                revision=self.revision,
                dtype="auto",
                device_map="auto",
                low_cpu_mem_usage=True,
            ).eval()
        except AdapterError as exc:
            self._load_error = exc
            raise
        except Exception as exc:
            error = ModelLoadError(
                f"Could not load {self.model_id} at revision {self.revision}: {exc}"
            )
            self._load_error = error
            raise error from exc

        self._dependencies = dependencies
        self._processor = processor
        self._model = model
        return (perf_counter_ns() - load_start_ns) / 1_000_000

    def _cuda_is_active(self) -> bool:
        if self._dependencies is None or self._model is None:
            return False
        cuda = getattr(self._dependencies.torch, "cuda", None)
        is_available = getattr(cuda, "is_available", None)
        return (
            callable(is_available)
            and bool(is_available())
            and str(self._model.device).casefold().startswith("cuda")
        )

    def _synchronize_cuda(self) -> None:
        if not self._cuda_is_active():
            return
        self._dependencies.torch.cuda.synchronize(self._model.device)

    def _reset_peak_gpu_memory(self) -> None:
        if not self._cuda_is_active():
            return
        self._dependencies.torch.cuda.reset_peak_memory_stats(self._model.device)

    def _peak_gpu_memory_mb(self) -> float | None:
        if not self._cuda_is_active():
            return None
        allocated = self._dependencies.torch.cuda.max_memory_allocated(
            self._model.device
        )
        return float(allocated) / (1024 * 1024)

    def _resolve_media(self, task: EvaluationTask) -> list[Path]:
        if not task.media:
            raise AdapterInputError(
                f"task '{task.id}' has no image media for the Qwen3-VL backend"
            )

        resolved: list[Path] = []
        for item in task.media:
            path = Path(item)
            path = path if path.is_absolute() else self.media_root / path
            if not path.is_file():
                raise AdapterInputError(
                    f"media for task '{task.id}' does not exist: {path}"
                )
            resolved.append(path.resolve())
        return resolved

    def _is_out_of_memory(self, exc: Exception) -> bool:
        if "out of memory" in str(exc).casefold():
            return True
        if self._dependencies is None:
            return False
        cuda = getattr(self._dependencies.torch, "cuda", None)
        error_type = getattr(cuda, "OutOfMemoryError", None)
        return isinstance(error_type, type) and isinstance(exc, error_type)

    def generate(self, task: EvaluationTask) -> ModelOutput:
        media_paths = self._resolve_media(task)
        model_load_ms = self._ensure_loaded()
        assert self._dependencies is not None

        images: list[Any] = []
        try:
            media_start_ns = perf_counter_ns()
            for path in media_paths:
                with self._dependencies.image_module.open(path) as source:
                    images.append(source.convert("RGB"))
            media_load_ms = (perf_counter_ns() - media_start_ns) / 1_000_000

            preprocess_start_ns = perf_counter_ns()
            content = [
                {"type": "image", "image": image}
                for image in images
            ]
            content.append({"type": "text", "text": task.prompt})
            messages = [{"role": "user", "content": content}]

            inputs = self._processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            )
            inputs = inputs.to(self._model.device)
            self._synchronize_cuda()
            preprocessing_ms = (
                perf_counter_ns() - preprocess_start_ns
            ) / 1_000_000
            prompt_tokens = int(inputs["input_ids"].shape[-1])

            self._reset_peak_gpu_memory()
            self._synchronize_cuda()
            generation_start_ns = perf_counter_ns()
            first_token_timer = _FirstTokenTimer(self._synchronize_cuda)
            with self._dependencies.torch.inference_mode():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    logits_processor=[first_token_timer],
                )
            self._synchronize_cuda()
            generation_ms = (
                perf_counter_ns() - generation_start_ns
            ) / 1_000_000
            ttft_ms = (
                (first_token_timer.first_token_ns - generation_start_ns)
                / 1_000_000
                if first_token_timer.first_token_ns is not None
                else None
            )
            peak_gpu_memory_mb = self._peak_gpu_memory_mb()

            trimmed_ids = [
                output_ids[prompt_tokens:] for output_ids in generated_ids
            ]
            decode_start_ns = perf_counter_ns()
            text = self._processor.batch_decode(
                trimmed_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0].strip()
            text_decode_ms = (perf_counter_ns() - decode_start_ns) / 1_000_000
            output_tokens = len(trimmed_ids[0])
            output_tokens_per_second = (
                output_tokens / (generation_ms / 1000)
                if generation_ms > 0
                else None
            )
            decode_duration_ms = (
                generation_ms - ttft_ms if ttft_ms is not None else None
            )
            decode_tokens_per_second = (
                (output_tokens - 1) / (decode_duration_ms / 1000)
                if output_tokens > 1
                and decode_duration_ms is not None
                and decode_duration_ms > 0
                else None
            )
        except Exception as exc:
            if self._is_out_of_memory(exc):
                raise AdapterOutOfMemoryError(str(exc)) from exc
            raise
        finally:
            for image in images:
                image.close()

        return ModelOutput(
            text=text,
            backend=self.name,
            model_revision=self.revision,
            usage={
                "model_id": self.model_id,
                "model_revision": self.revision,
                "processor_revision": self.revision,
                "device": str(self._model.device),
                "dtype": str(getattr(self._model, "dtype", "auto")),
                "do_sample": False,
                "max_new_tokens": self.max_new_tokens,
                "input_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "model_load_ms": model_load_ms,
                "media_load_ms": media_load_ms,
                "preprocessing_ms": preprocessing_ms,
                "ttft_ms": ttft_ms,
                "generation_ms": generation_ms,
                "text_decode_ms": text_decode_ms,
                "output_tokens_per_second": output_tokens_per_second,
                "decode_tokens_per_second": decode_tokens_per_second,
                "peak_gpu_memory_mb": peak_gpu_memory_mb,
            },
        )

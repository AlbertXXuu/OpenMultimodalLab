"""Shared runtime contract for local Transformers image-text adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Callable

from ..models import EvaluationTask, ModelOutput
from .errors import (
    AdapterError,
    AdapterInputError,
    AdapterOutOfMemoryError,
    ModelLoadError,
)


@dataclass(frozen=True, slots=True)
class TransformersDependencies:
    """Late-imported packages required by a Transformers VLM backend."""

    torch: Any
    auto_model: Any
    auto_processor: Any
    image_module: Any


class FirstTokenTimer:
    """Transformers logits hook used to mark the first generated token."""

    def __init__(self, synchronize: Callable[[], None]) -> None:
        self._synchronize = synchronize
        self.first_token_ns: int | None = None

    def __call__(self, input_ids: Any, scores: Any) -> Any:
        if self.first_token_ns is None:
            self._synchronize()
            self.first_token_ns = perf_counter_ns()
        return scores


class TransformersImageTextAdapter:
    """Reusable, auditable execution path for native Transformers VLMs."""

    name = ""
    display_name = ""

    def __init__(
        self,
        *,
        media_root: str | Path,
        model_id: str,
        revision: str,
        max_new_tokens: int,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must be non-empty")
        if not revision.strip():
            raise ValueError("revision must be non-empty")
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be at least 1")
        if not self.name or not self.display_name:
            raise TypeError("adapter subclasses must define name and display_name")

        self.media_root = Path(media_root)
        self.model_id = model_id.strip()
        self.revision = revision.strip()
        self.max_new_tokens = max_new_tokens
        self._dependencies: TransformersDependencies | None = None
        self._model: Any = None
        self._processor: Any = None
        self._load_error: AdapterError | None = None

    def _load_runtime_dependencies(self) -> TransformersDependencies:
        raise NotImplementedError

    def _model_load_kwargs(
        self,
        dependencies: TransformersDependencies,
    ) -> dict[str, Any]:
        return {
            "dtype": "auto",
            "device_map": "auto",
            "low_cpu_mem_usage": True,
        }

    def _move_inputs_to_model(self, inputs: Any) -> Any:
        return inputs.to(self._model.device)

    def _ensure_loaded(self) -> float:
        if self._model is not None and self._processor is not None:
            return 0.0
        if self._load_error is not None:
            raise self._load_error

        load_start_ns = perf_counter_ns()
        try:
            dependencies = self._load_runtime_dependencies()
            processor = dependencies.auto_processor.from_pretrained(
                self.model_id,
                revision=self.revision,
            )
            model = dependencies.auto_model.from_pretrained(
                self.model_id,
                revision=self.revision,
                **self._model_load_kwargs(dependencies),
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
        if self._cuda_is_active():
            self._dependencies.torch.cuda.synchronize(self._model.device)

    def _reset_peak_gpu_memory(self) -> None:
        if self._cuda_is_active():
            self._dependencies.torch.cuda.reset_peak_memory_stats(
                self._model.device
            )

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
                f"task '{task.id}' has no image media for the "
                f"{self.display_name} backend"
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

    def _processor_usage(self) -> dict[str, Any]:
        image_processor = getattr(self._processor, "image_processor", None)
        usage: dict[str, Any] = {
            "model_class": type(self._model).__name__,
            "processor_class": type(self._processor).__name__,
            "chat_template": "processor.apply_chat_template",
        }
        if image_processor is not None:
            usage["image_processor_class"] = type(image_processor).__name__
            for attribute in (
                "do_resize",
                "size",
                "max_image_size",
                "min_pixels",
                "max_pixels",
                "patch_size",
                "temporal_patch_size",
                "merge_size",
                "do_image_splitting",
            ):
                value = self._json_compatible(
                    getattr(image_processor, attribute, None)
                )
                if value is not None:
                    usage[f"image_processor_{attribute}"] = value
        return usage

    @classmethod
    def _json_compatible(cls, value: Any) -> Any:
        if value is None or isinstance(value, (bool, float, int, str)):
            return value
        if is_dataclass(value) and not isinstance(value, type):
            value = asdict(value)
        if isinstance(value, Mapping):
            converted: dict[str, Any] = {}
            for key, item in value.items():
                converted_item = cls._json_compatible(item)
                if converted_item is not None:
                    converted[str(key)] = converted_item
            return converted or None
        if isinstance(value, Sequence) and not isinstance(
            value,
            (bytes, bytearray, str),
        ):
            converted_items = [cls._json_compatible(item) for item in value]
            if all(item is not None for item in converted_items):
                return converted_items
        return None

    @staticmethod
    def _input_tensor_shapes(inputs: Mapping[str, Any]) -> dict[str, list[int]]:
        shapes: dict[str, list[int]] = {}
        for name, value in inputs.items():
            shape = getattr(value, "shape", None)
            if shape is None:
                continue
            try:
                dimensions = [int(dimension) for dimension in shape]
            except (TypeError, ValueError):
                continue
            shapes[str(name)] = dimensions
        return shapes

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
            inputs = self._move_inputs_to_model(inputs)
            self._synchronize_cuda()
            preprocessing_ms = (
                perf_counter_ns() - preprocess_start_ns
            ) / 1_000_000
            prompt_tokens = int(inputs["input_ids"].shape[-1])
            input_tensor_shapes = self._input_tensor_shapes(inputs)

            self._reset_peak_gpu_memory()
            self._synchronize_cuda()
            generation_start_ns = perf_counter_ns()
            first_token_timer = FirstTokenTimer(self._synchronize_cuda)
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

        usage = {
            "model_id": self.model_id,
            "model_revision": self.revision,
            "processor_revision": self.revision,
            "device": str(self._model.device),
            "dtype": str(getattr(self._model, "dtype", "auto")),
            "do_sample": False,
            "max_new_tokens": self.max_new_tokens,
            "input_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "input_tensor_shapes": input_tensor_shapes,
            "model_load_ms": model_load_ms,
            "media_load_ms": media_load_ms,
            "preprocessing_ms": preprocessing_ms,
            "ttft_ms": ttft_ms,
            "generation_ms": generation_ms,
            "text_decode_ms": text_decode_ms,
            "output_tokens_per_second": output_tokens_per_second,
            "decode_tokens_per_second": decode_tokens_per_second,
            "peak_gpu_memory_mb": peak_gpu_memory_mb,
        }
        usage.update(self._processor_usage())
        return ModelOutput(
            text=text,
            backend=self.name,
            model_revision=self.revision,
            usage=usage,
        )

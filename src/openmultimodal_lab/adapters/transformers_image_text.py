"""Shared runtime contract for local Transformers visual-text adapters."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from inspect import signature
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Callable

from ..models import EvaluationTask, ModelOutput
from ..privacy import portable_path_reference, redact_local_paths
from .errors import (
    AdapterError,
    AdapterInputError,
    AdapterOutOfMemoryError,
    AdapterTimeoutError,
    ModelLoadError,
)


DEFAULT_VIDEO_NUM_FRAMES = 8
MAX_IMAGE_FILE_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_VIDEO_FILE_BYTES = 256 * 1024 * 1024
MAX_VIDEO_DURATION_SECONDS = 60.0
MAX_VIDEO_TOTAL_FRAMES = 3600
MAX_VIDEO_PIXELS = 3840 * 2160
SUPPORTED_IMAGE_SUFFIXES = frozenset(
    {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
)
SUPPORTED_VIDEO_SUFFIXES = frozenset(
    {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}
)


@dataclass(frozen=True, slots=True)
class TransformersDependencies:
    """Late-imported packages required by a Transformers VLM backend."""

    torch: Any
    auto_model: Any
    auto_processor: Any
    image_module: Any
    video_loader: Callable[..., Any] | None = None


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
        video_num_frames: int = DEFAULT_VIDEO_NUM_FRAMES,
    ) -> None:
        if not model_id.strip():
            raise ValueError("model_id must be non-empty")
        if not revision.strip():
            raise ValueError("revision must be non-empty")
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be at least 1")
        if (
            not isinstance(video_num_frames, int)
            or isinstance(video_num_frames, bool)
            or video_num_frames < 1
        ):
            raise ValueError("video_num_frames must be an integer above 0")
        if not self.name or not self.display_name:
            raise TypeError("adapter subclasses must define name and display_name")

        self.media_root = Path(media_root)
        self.model_id = model_id.strip()
        self.revision = revision.strip()
        self.max_new_tokens = max_new_tokens
        self.video_num_frames = video_num_frames
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
                f"Could not load {self.model_id} at revision {self.revision}: "
                f"{type(exc).__name__}: {redact_local_paths(exc)}"
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
                f"task '{task.id}' has no visual media for the "
                f"{self.display_name} backend"
            )

        resolved: list[Path] = []
        for item in task.media:
            path = Path(item)
            path = path if path.is_absolute() else self.media_root / path
            label = portable_path_reference(item)
            if not path.is_file():
                raise AdapterInputError(
                    f"media for task '{task.id}' does not exist: {label}"
                )
            resolved_path = path.resolve()
            suffix = resolved_path.suffix.casefold()
            if suffix not in SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_SUFFIXES:
                supported = ", ".join(
                    sorted(SUPPORTED_IMAGE_SUFFIXES | SUPPORTED_VIDEO_SUFFIXES)
                )
                raise AdapterInputError(
                    f"media for task '{task.id}' has unsupported extension "
                    f"'{suffix or '<none>'}': {label}; supported: "
                    f"{supported}"
                )
            size_bytes = resolved_path.stat().st_size
            size_limit = (
                MAX_VIDEO_FILE_BYTES
                if suffix in SUPPORTED_VIDEO_SUFFIXES
                else MAX_IMAGE_FILE_BYTES
            )
            if size_bytes > size_limit:
                raise AdapterInputError(
                    f"media for task '{task.id}' exceeds the "
                    f"{size_limit // (1024 * 1024)} MiB safety limit: "
                    f"{label}"
                )
            resolved.append(resolved_path)
        return resolved

    @staticmethod
    def _media_type(path: Path) -> str:
        return (
            "video"
            if path.suffix.casefold() in SUPPORTED_VIDEO_SUFFIXES
            else "image"
        )

    def _is_out_of_memory(self, exc: Exception) -> bool:
        if "out of memory" in str(exc).casefold():
            return True
        if self._dependencies is None:
            return False
        cuda = getattr(self._dependencies.torch, "cuda", None)
        error_type = getattr(cuda, "OutOfMemoryError", None)
        return isinstance(error_type, type) and isinstance(exc, error_type)

    def _decode_video(
        self,
        task: EvaluationTask,
        path: Path,
    ) -> tuple[Any, int, Any, list[int]]:
        assert self._dependencies is not None
        if self._dependencies.video_loader is None:
            raise AdapterInputError(
                f"video decoding is unavailable for task '{task.id}'; "
                "install the backend's optional dependencies"
            )
        sampled_indices: list[int] | None = None

        def bounded_sample_indices(metadata: Any, **kwargs: Any) -> Any:
            nonlocal sampled_indices
            indices = self._sample_video_indices(metadata, **kwargs)
            sampled_indices = [int(index) for index in indices]
            return indices

        try:
            decoded = self._dependencies.video_loader(
                str(path),
                num_frames=self.video_num_frames,
                backend="pyav",
                sample_indices_fn=bounded_sample_indices,
            )
        except Exception as exc:
            raise AdapterInputError(
                f"could not decode video for task '{task.id}': {path.name}: "
                f"{type(exc).__name__}: {redact_local_paths(exc)}"
            ) from exc
        if not isinstance(decoded, tuple) or len(decoded) != 2:
            raise AdapterInputError(
                f"video decoder returned no provenance metadata for task "
                f"'{task.id}': {path}"
            )
        frames, metadata = decoded
        shape = getattr(frames, "shape", None)
        try:
            frame_count = int(shape[0])
        except (IndexError, TypeError, ValueError) as exc:
            raise AdapterInputError(
                f"video decoder returned no frame dimension for task "
                f"'{task.id}': {path}"
            ) from exc
        if frame_count < 1:
            raise AdapterInputError(
                f"video decoder returned no frames for task '{task.id}': "
                f"{path}"
            )
        if sampled_indices is None:
            raise AdapterInputError(
                f"video decoder did not invoke bounded sampling for task "
                f"'{task.id}': {path.name}"
            )
        return frames, frame_count, metadata, sampled_indices

    def _video_sampling_provenance(
        self,
        metadata: Any,
        sampled_indices: list[int],
        decoded_frame_count: int,
    ) -> dict[str, Any]:
        sampling = self._json_compatible(metadata)
        if not isinstance(sampling, dict):
            sampling = {}
        sampling.update(
            {
                "source_frame_count": int(metadata.total_num_frames),
                "fps": float(metadata.fps),
                "duration_seconds": float(metadata.duration),
                "dimensions": [int(metadata.width), int(metadata.height)],
                "sampled_indices": sampled_indices,
                "decoded_frame_count": decoded_frame_count,
            }
        )
        return sampling

    def _sample_video_indices(
        self,
        metadata: Any,
        **_: Any,
    ) -> Any:
        """Validate short-video metadata before bounded uniform decoding."""

        try:
            total_frames = int(metadata.total_num_frames)
            fps = float(metadata.fps)
            duration = float(metadata.duration)
            width = int(metadata.width)
            height = int(metadata.height)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("video metadata is incomplete") from exc
        if total_frames < 1 or total_frames > MAX_VIDEO_TOTAL_FRAMES:
            raise ValueError(
                f"video frame count must be 1-{MAX_VIDEO_TOTAL_FRAMES}; "
                f"received {total_frames}"
            )
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("video FPS must be a finite number above 0")
        if not math.isfinite(duration) or duration < 0:
            raise ValueError(
                "video duration must be a finite non-negative number"
            )
        effective_duration = max(duration, total_frames / fps)
        if effective_duration > MAX_VIDEO_DURATION_SECONDS:
            raise ValueError(
                f"video duration exceeds the "
                f"{MAX_VIDEO_DURATION_SECONDS:g} second safety limit"
            )
        if width < 1 or height < 1 or width * height > MAX_VIDEO_PIXELS:
            raise ValueError(
                f"video dimensions must contain 1-{MAX_VIDEO_PIXELS} "
                f"pixels per frame; received {width}x{height}"
            )
        import numpy as np

        return np.asarray(
            [
                index * total_frames // self.video_num_frames
                for index in range(self.video_num_frames)
            ],
            dtype=int,
        )

    @staticmethod
    def _validate_image_dimensions(
        task: EvaluationTask,
        source: Any,
    ) -> None:
        try:
            width, height = source.size
            width = int(width)
            height = int(height)
        except (AttributeError, TypeError, ValueError) as exc:
            raise AdapterInputError(
                f"image metadata is incomplete for task '{task.id}'"
            ) from exc
        if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
            raise AdapterInputError(
                f"image for task '{task.id}' must contain "
                f"1-{MAX_IMAGE_PIXELS} pixels; received {width}x{height}"
            )

    def _processor_usage(self) -> dict[str, Any]:
        image_processor = getattr(self._processor, "image_processor", None)
        video_processor = getattr(self._processor, "video_processor", None)
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
        if video_processor is not None:
            usage["video_processor_class"] = type(video_processor).__name__
            for attribute in (
                "do_resize",
                "size",
                "min_pixels",
                "max_pixels",
                "patch_size",
                "temporal_patch_size",
                "merge_size",
                "min_frames",
                "max_frames",
            ):
                value = self._json_compatible(
                    getattr(video_processor, attribute, None)
                )
                if value is not None:
                    usage[f"video_processor_{attribute}"] = value
        return usage

    @classmethod
    def _json_compatible(cls, value: Any) -> Any:
        if value is None or isinstance(value, (bool, float, int, str)):
            return value
        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            value = tolist()
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

    def _processor_pad_token_id(self) -> int | None:
        """Prefer the pinned tokenizer over inconsistent top-level configs."""

        tokenizer = getattr(self._processor, "tokenizer", None)
        value = getattr(tokenizer, "pad_token_id", None)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
        return None

    def generate(
        self,
        task: EvaluationTask,
        *,
        timeout_seconds: float | None = None,
    ) -> ModelOutput:
        if timeout_seconds is not None and (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite number above 0")

        media_paths = self._resolve_media(task)
        model_load_ms = self._ensure_loaded()
        assert self._dependencies is not None
        inference_start_ns = perf_counter_ns()

        images: list[Any] = []
        media_types = [self._media_type(path) for path in media_paths]
        image_count = media_types.count("image")
        video_count = media_types.count("video")
        video_decode_ms = 0.0
        video_frame_counts: list[int] = []
        video_metadata: list[Any] = []
        video_sampling: list[dict[str, Any]] = []
        try:
            media_start_ns = perf_counter_ns()
            content: list[dict[str, Any]] = []
            for path, media_type in zip(
                media_paths,
                media_types,
                strict=True,
            ):
                if media_type == "video":
                    video_decode_start_ns = perf_counter_ns()
                    (
                        frames,
                        frame_count,
                        metadata,
                        sampled_indices,
                    ) = self._decode_video(
                        task,
                        path,
                    )
                    video_decode_ms += (
                        perf_counter_ns() - video_decode_start_ns
                    ) / 1_000_000
                    video_frame_counts.append(frame_count)
                    video_metadata.append(metadata)
                    video_sampling.append(
                        self._video_sampling_provenance(
                            metadata,
                            sampled_indices,
                            frame_count,
                        )
                    )
                    content.append({"type": "video", "video": frames})
                    continue
                try:
                    with self._dependencies.image_module.open(path) as source:
                        self._validate_image_dimensions(task, source)
                        image = source.convert("RGB")
                        images.append(image)
                        content.append({"type": "image", "image": image})
                except AdapterInputError:
                    raise
                except Exception as exc:
                    raise AdapterInputError(
                        f"could not load image for task '{task.id}': "
                        f"{path.name}: {type(exc).__name__}: "
                        f"{redact_local_paths(exc)}"
                    ) from exc
            media_load_ms = (perf_counter_ns() - media_start_ns) / 1_000_000

            preprocess_start_ns = perf_counter_ns()
            content.append({"type": "text", "text": task.prompt})
            messages = [{"role": "user", "content": content}]
            template_arguments: dict[str, Any] = {
                "tokenize": True,
                "add_generation_prompt": True,
                "return_dict": True,
                "return_tensors": "pt",
            }
            if video_count:
                video_processor_arguments = {
                    "do_sample_frames": False,
                    "video_metadata": video_metadata,
                }
                template_parameters = signature(
                    self._processor.apply_chat_template
                ).parameters
                if "processor_kwargs" in template_parameters:
                    template_arguments["processor_kwargs"] = (
                        video_processor_arguments
                    )
                else:
                    template_arguments.update(video_processor_arguments)
            inputs = self._processor.apply_chat_template(
                messages,
                **template_arguments,
            )
            inputs = self._move_inputs_to_model(inputs)
            self._synchronize_cuda()
            preprocessing_ms = (
                perf_counter_ns() - preprocess_start_ns
            ) / 1_000_000
            prompt_tokens = int(inputs["input_ids"].shape[-1])
            input_tensor_shapes = self._input_tensor_shapes(inputs)
            pad_token_id = self._processor_pad_token_id()

            self._reset_peak_gpu_memory()
            self._synchronize_cuda()
            generation_start_ns = perf_counter_ns()
            first_token_timer = FirstTokenTimer(self._synchronize_cuda)
            generation_arguments: dict[str, Any] = {
                "max_new_tokens": self.max_new_tokens,
                "do_sample": False,
                "logits_processor": [first_token_timer],
            }
            if pad_token_id is not None:
                generation_arguments["pad_token_id"] = pad_token_id
            if timeout_seconds is not None:
                elapsed_seconds = (
                    perf_counter_ns() - inference_start_ns
                ) / 1_000_000_000
                remaining_seconds = timeout_seconds - elapsed_seconds
                if remaining_seconds <= 0:
                    raise AdapterTimeoutError(
                        f"inference exceeded {timeout_seconds:g} seconds "
                        "before generation started"
                    )
                generation_arguments["max_time"] = remaining_seconds
            with self._dependencies.torch.inference_mode():
                generated_ids = self._model.generate(
                    **inputs,
                    **generation_arguments,
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
            inference_seconds = (
                perf_counter_ns() - inference_start_ns
            ) / 1_000_000_000
            if (
                timeout_seconds is not None
                and inference_seconds >= timeout_seconds
            ):
                raise AdapterTimeoutError(
                    f"inference exceeded {timeout_seconds:g} seconds"
                )

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
            inference_seconds = (
                perf_counter_ns() - inference_start_ns
            ) / 1_000_000_000
            if (
                timeout_seconds is not None
                and inference_seconds >= timeout_seconds
            ):
                raise AdapterTimeoutError(
                    f"inference exceeded {timeout_seconds:g} seconds "
                    "during text decoding"
                )
        except Exception as exc:
            if self._is_out_of_memory(exc):
                raise AdapterOutOfMemoryError(
                    redact_local_paths(exc)
                ) from exc
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
            "pad_token_id": pad_token_id,
            "media_types": media_types,
            "image_count": image_count,
            "video_count": video_count,
            "video_num_frames": (
                self.video_num_frames if video_count else None
            ),
            "video_frame_counts": video_frame_counts,
            "video_sampling": video_sampling,
            "media_limits": {
                "max_image_file_bytes": MAX_IMAGE_FILE_BYTES,
                "max_image_pixels": MAX_IMAGE_PIXELS,
                "max_video_file_bytes": MAX_VIDEO_FILE_BYTES,
                "max_video_duration_seconds": MAX_VIDEO_DURATION_SECONDS,
                "max_video_total_frames": MAX_VIDEO_TOTAL_FRAMES,
                "max_video_pixels_per_frame": MAX_VIDEO_PIXELS,
            },
            "input_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "input_tensor_shapes": input_tensor_shapes,
            "model_load_ms": model_load_ms,
            "media_load_ms": media_load_ms,
            "video_decode_ms": video_decode_ms,
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

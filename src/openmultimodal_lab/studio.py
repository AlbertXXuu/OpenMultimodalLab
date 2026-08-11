"""Dependency-free application services for the optional Ailumetra Studio."""

from __future__ import annotations

import gc
import math
import sys
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any

from .adapters import create_adapter
from .adapters.base import ModelAdapter
from .adapters.transformers_image_text import (
    SUPPORTED_IMAGE_SUFFIXES,
    SUPPORTED_VIDEO_SUFFIXES,
)
from .models import EvaluationTask, ScoringConfig
from .privacy import redact_local_paths
from .reporting import format_summary, load_records, summarize


STUDIO_BRAND = "Ailumetra"
STUDIO_NAME = "Ailumetra Studio"
STUDIO_TAGLINE = "Measure multimodal AI. See clearly."
DEVELOPER_ID = "ALONICA"

BACKEND_LABELS = {
    "qwen3-vl": "Qwen3-VL 2B",
    "smolvlm2": "SmolVLM2 500M",
    "mock": "Mock · interface test only",
}
PLAYGROUND_PROMPT_MAX_CHARS = 4_000
PLAYGROUND_MAX_NEW_TOKENS = 256
PLAYGROUND_MAX_TIMEOUT_SECONDS = 600.0
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_REPORT_ROWS = 2_000


class StudioError(ValueError):
    """Base error that can be shown safely by the local Studio UI."""


class StudioInputError(StudioError):
    """Raised when a Studio input does not meet its documented boundary."""


@dataclass(frozen=True, slots=True)
class PlaygroundResult:
    """One unscored interactive inference and its normalized runtime metrics."""

    response_text: str
    backend: str
    model_revision: str
    latency_ms: float
    usage: Mapping[str, Any]
    media_kind: str


@dataclass(frozen=True, slots=True)
class ReportView:
    """Safe, UI-ready projection of a persisted run record file."""

    filename: str
    summary: Mapping[str, Any]
    summary_text: str
    rows: tuple[tuple[Any, ...], ...]


def _finite_non_negative(value: object) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    ):
        return float(value)
    return None


def _validated_media(path_value: str | Path, media_kind: str) -> Path:
    if media_kind not in {"image", "video"}:
        raise StudioInputError("media kind must be image or video")
    try:
        path = Path(path_value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise StudioInputError("uploaded media is no longer available") from exc
    if not path.is_file():
        raise StudioInputError("uploaded media must be a regular file")

    suffix = path.suffix.casefold()
    allowed_suffixes = (
        SUPPORTED_IMAGE_SUFFIXES
        if media_kind == "image"
        else SUPPORTED_VIDEO_SUFFIXES
    )
    if suffix not in allowed_suffixes:
        supported = ", ".join(sorted(allowed_suffixes))
        raise StudioInputError(
            f"unsupported {media_kind} type '{suffix or 'none'}'; "
            f"supported: {supported}"
        )

    size_limit = MAX_IMAGE_BYTES if media_kind == "image" else MAX_VIDEO_BYTES
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise StudioInputError("uploaded media cannot be inspected") from exc
    if size <= 0:
        raise StudioInputError("uploaded media is empty")
    if size > size_limit:
        raise StudioInputError(
            f"{media_kind} exceeds the {size_limit // (1024 * 1024)} MiB limit"
        )
    return path


def select_media(
    image_path: str | Path | None,
    video_path: str | Path | None,
) -> tuple[Path, str]:
    """Require exactly one upload and return its validated path and kind."""

    supplied = [
        (image_path, "image"),
        (video_path, "video"),
    ]
    selected = [(path, kind) for path, kind in supplied if path]
    if not selected:
        raise StudioInputError("upload one image, document screenshot, or video")
    if len(selected) > 1:
        raise StudioInputError("use either the image input or video input, not both")
    path_value, media_kind = selected[0]
    return _validated_media(path_value, media_kind), media_kind


def _validate_playground_parameters(
    backend: str,
    prompt: str,
    max_new_tokens: int,
    timeout_seconds: float,
) -> tuple[str, int, float]:
    if backend not in BACKEND_LABELS:
        raise StudioInputError(f"unsupported backend: {backend}")
    if not isinstance(prompt, str) or not prompt.strip():
        raise StudioInputError("prompt cannot be empty")
    prompt = prompt.strip()
    if len(prompt) > PLAYGROUND_PROMPT_MAX_CHARS:
        raise StudioInputError(
            f"prompt exceeds {PLAYGROUND_PROMPT_MAX_CHARS} characters"
        )
    if (
        not isinstance(max_new_tokens, int)
        or isinstance(max_new_tokens, bool)
        or not 1 <= max_new_tokens <= PLAYGROUND_MAX_NEW_TOKENS
    ):
        raise StudioInputError(
            f"max new tokens must be from 1 to {PLAYGROUND_MAX_NEW_TOKENS}"
        )
    if (
        not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or not math.isfinite(float(timeout_seconds))
        or not 1 <= float(timeout_seconds) <= PLAYGROUND_MAX_TIMEOUT_SECONDS
    ):
        raise StudioInputError(
            "timeout must be from 1 to "
            f"{int(PLAYGROUND_MAX_TIMEOUT_SECONDS)} seconds"
        )
    return prompt, max_new_tokens, float(timeout_seconds)


class StudioRuntime:
    """Own one lazy model adapter and serialize local GPU access."""

    def __init__(
        self,
        adapter_factory: Callable[..., ModelAdapter] = create_adapter,
    ) -> None:
        self._adapter_factory = adapter_factory
        self._adapter: ModelAdapter | None = None
        self._backend: str | None = None
        self._lock = threading.RLock()

    def _release_adapter(self) -> None:
        self._adapter = None
        self._backend = None
        gc.collect()
        torch = sys.modules.get("torch")
        cuda = getattr(torch, "cuda", None) if torch is not None else None
        if cuda is not None:
            try:
                if bool(cuda.is_available()):
                    cuda.empty_cache()
            except (AttributeError, RuntimeError):
                pass

    def close(self) -> None:
        """Release the cached model and any reclaimable CUDA allocation."""

        with self._lock:
            self._release_adapter()

    def _adapter_for(
        self,
        backend: str,
        media_root: Path,
        max_new_tokens: int,
    ) -> ModelAdapter:
        if self._adapter is None or self._backend != backend:
            self._release_adapter()
            self._adapter = self._adapter_factory(
                backend,
                media_root=media_root,
                max_new_tokens=max_new_tokens,
            )
            self._backend = backend
        if hasattr(self._adapter, "media_root"):
            setattr(self._adapter, "media_root", media_root)
        if hasattr(self._adapter, "max_new_tokens"):
            setattr(self._adapter, "max_new_tokens", max_new_tokens)
        return self._adapter

    def run_playground(
        self,
        *,
        backend: str,
        prompt: str,
        image_path: str | Path | None,
        video_path: str | Path | None,
        max_new_tokens: int,
        timeout_seconds: float,
    ) -> PlaygroundResult:
        """Run one local, explicitly unscored, interactive inference."""

        prompt, max_new_tokens, timeout_seconds = _validate_playground_parameters(
            backend,
            prompt,
            max_new_tokens,
            timeout_seconds,
        )
        media_path, media_kind = select_media(image_path, video_path)
        task = EvaluationTask(
            id="ailumetra-playground",
            prompt=prompt,
            media=(media_path.name,),
            scoring=ScoringConfig(type="keyword_coverage"),
            metadata={
                "dataset_version": "ailumetra-studio-session",
                "category": "unscored-playground",
            },
        )

        with self._lock:
            adapter = self._adapter_for(
                backend,
                media_path.parent,
                max_new_tokens,
            )
            start_ns = perf_counter_ns()
            output = adapter.generate(task, timeout_seconds=timeout_seconds)
            latency_ms = (perf_counter_ns() - start_ns) / 1_000_000

        return PlaygroundResult(
            response_text=output.text,
            backend=output.backend,
            model_revision=output.model_revision,
            latency_ms=latency_ms,
            usage=dict(output.usage),
            media_kind=media_kind,
        )


def load_report_view(path_value: str | Path) -> ReportView:
    """Load an existing run without exposing its local absolute path."""

    try:
        path = Path(path_value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise StudioInputError("report file is no longer available") from exc
    if path.suffix.casefold() != ".jsonl":
        raise StudioInputError("report input must be a .jsonl run record file")

    records = load_records(path)
    if len(records) > MAX_REPORT_ROWS:
        raise StudioInputError(
            f"report contains more than {MAX_REPORT_ROWS} records"
        )
    summary = summarize(records)
    rows: list[tuple[Any, ...]] = []
    for record in records:
        usage = record.get("usage")
        usage = usage if isinstance(usage, Mapping) else {}
        rows.append(
            (
                record.get("phase", "measurement"),
                record.get("repetition", 1),
                record.get("task_id", ""),
                record.get("status", ""),
                record.get("score"),
                round(float(record.get("latency_ms", 0.0)), 3),
                _finite_non_negative(usage.get("ttft_ms")),
                _finite_non_negative(usage.get("output_tokens_per_second")),
                _finite_non_negative(usage.get("peak_gpu_memory_mb")),
            )
        )
    return ReportView(
        filename=path.name,
        summary=summary,
        summary_text=format_summary(dict(summary)),
        rows=tuple(rows),
    )


def safe_studio_error(exc: BaseException) -> str:
    """Return a short error without user-specific local filesystem paths."""

    detail = redact_local_paths(exc)
    return f"{type(exc).__name__}: {detail}"

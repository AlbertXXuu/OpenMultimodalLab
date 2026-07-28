"""Core data structures shared by datasets, adapters, runners, and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class EvaluationTask:
    """A single versioned benchmark task."""

    id: str
    prompt: str
    media: tuple[str, ...] = ()
    expected_keywords: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvaluationTask":
        task_id = value.get("id")
        prompt = value.get("prompt")
        media = value.get("media", [])
        expected_keywords = value.get("expected_keywords", [])
        metadata = value.get("metadata", {})

        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("'id' must be a non-empty string")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("'prompt' must be a non-empty string")
        if not isinstance(media, list) or not all(isinstance(item, str) for item in media):
            raise ValueError("'media' must be a list of strings")
        if not isinstance(expected_keywords, list) or not all(
            isinstance(item, str) and item.strip() for item in expected_keywords
        ):
            raise ValueError("'expected_keywords' must be a list of non-empty strings")
        if not isinstance(metadata, dict):
            raise ValueError("'metadata' must be an object")

        return cls(
            id=task_id.strip(),
            prompt=prompt.strip(),
            media=tuple(media),
            expected_keywords=tuple(item.strip() for item in expected_keywords),
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class ModelOutput:
    """Normalized output returned by every model adapter."""

    text: str
    backend: str
    model_revision: str
    usage: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Serializable result for one task and one adapter invocation."""

    schema_version: str
    task_id: str
    category: str
    backend: str
    model_revision: str
    timestamp_utc: str
    status: str
    response_text: str | None
    latency_ms: float
    score: float | None
    matched_keywords: tuple[str, ...]
    expected_keywords: tuple[str, ...]
    media: tuple[str, ...]
    usage: Mapping[str, Any]
    error: str | None

"""Core data structures shared by datasets, adapters, runners, and reports."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping


LEGACY_TASK_SCHEMA_VERSION = "1.0"
STRUCTURED_TASK_SCHEMA_VERSION = "1.1"
CURRENT_TASK_SCHEMA_VERSION = "1.2"
SUPPORTED_TASK_SCHEMA_VERSIONS = frozenset(
    {
        LEGACY_TASK_SCHEMA_VERSION,
        STRUCTURED_TASK_SCHEMA_VERSION,
        CURRENT_TASK_SCHEMA_VERSION,
    }
)
SUPPORTED_SCORER_TYPES = frozenset(
    {
        "keyword_coverage",
        "normalized_exact_match",
        "attribute_groups",
        "numeric_tolerance",
    }
)


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """Validated deterministic scoring rule for one benchmark task."""

    type: str = "keyword_coverage"
    groups: tuple[tuple[str, ...], ...] = ()
    ordered: bool = False
    target: float | None = None
    absolute_tolerance: float | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ScoringConfig":
        scorer_type = value.get("type")
        groups = value.get("groups", [])
        ordered = value.get("ordered", False)
        target = value.get("target")
        absolute_tolerance = value.get("absolute_tolerance")

        if not isinstance(scorer_type, str) or not scorer_type.strip():
            raise ValueError("'scoring.type' must be a non-empty string")
        scorer_type = scorer_type.strip()
        if scorer_type not in SUPPORTED_SCORER_TYPES:
            supported = ", ".join(sorted(SUPPORTED_SCORER_TYPES))
            raise ValueError(
                f"unsupported scoring type '{scorer_type}'; supported: {supported}"
            )
        if not isinstance(ordered, bool):
            raise ValueError("'scoring.ordered' must be a boolean")
        if not isinstance(groups, list):
            raise ValueError("'scoring.groups' must be a list")
        if scorer_type == "numeric_tolerance":
            if groups:
                raise ValueError(
                    "'scoring.groups' is only supported by 'attribute_groups'"
                )
            if ordered:
                raise ValueError(
                    "'scoring.ordered' is only supported by 'attribute_groups'"
                )
            for field_name, field_value in (
                ("target", target),
                ("absolute_tolerance", absolute_tolerance),
            ):
                if (
                    not isinstance(field_value, (int, float))
                    or isinstance(field_value, bool)
                    or not math.isfinite(float(field_value))
                ):
                    raise ValueError(
                        f"'scoring.{field_name}' must be a finite number"
                    )
            if float(absolute_tolerance) < 0:
                raise ValueError(
                    "'scoring.absolute_tolerance' must be at least 0"
                )
            return cls(
                type=scorer_type,
                target=float(target),
                absolute_tolerance=float(absolute_tolerance),
            )

        if "target" in value or "absolute_tolerance" in value:
            raise ValueError(
                "'scoring.target' and 'scoring.absolute_tolerance' are only "
                "supported by 'numeric_tolerance'"
            )
        if scorer_type != "attribute_groups":
            if groups:
                raise ValueError(
                    "'scoring.groups' is only supported by 'attribute_groups'"
                )
            if ordered:
                raise ValueError(
                    "'scoring.ordered' is only supported by 'attribute_groups'"
                )
            return cls(type=scorer_type)

        if not isinstance(groups, list) or not groups:
            raise ValueError(
                "'scoring.groups' must be a non-empty list for 'attribute_groups'"
            )

        normalized_groups: list[tuple[str, ...]] = []
        for group_index, group in enumerate(groups, start=1):
            if not isinstance(group, list) or not group:
                raise ValueError(
                    f"'scoring.groups[{group_index}]' must be a non-empty list"
                )
            if not all(isinstance(term, str) and term.strip() for term in group):
                raise ValueError(
                    f"'scoring.groups[{group_index}]' must contain "
                    "non-empty strings"
                )
            normalized_group = tuple(term.strip() for term in group)
            if len({term.casefold() for term in normalized_group}) != len(
                normalized_group
            ):
                raise ValueError(
                    f"'scoring.groups[{group_index}]' must not contain "
                    "duplicate terms"
                )
            normalized_groups.append(normalized_group)

        return cls(
            type=scorer_type,
            groups=tuple(normalized_groups),
            ordered=ordered,
        )


@dataclass(frozen=True, slots=True)
class EvaluationTask:
    """A single versioned benchmark task."""

    id: str
    prompt: str
    schema_version: str = CURRENT_TASK_SCHEMA_VERSION
    media: tuple[str, ...] = ()
    expected_keywords: tuple[str, ...] = ()
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvaluationTask":
        schema_version = value.get("schema_version")
        task_id = value.get("id")
        prompt = value.get("prompt")
        media = value.get("media", [])
        expected_keywords = value.get("expected_keywords", [])
        scoring = value.get("scoring")
        metadata = value.get("metadata", {})

        if not isinstance(schema_version, str) or not schema_version.strip():
            raise ValueError("'schema_version' must be a non-empty string")
        schema_version = schema_version.strip()
        if schema_version not in SUPPORTED_TASK_SCHEMA_VERSIONS:
            raise ValueError(f"unsupported schema version '{schema_version}'")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("'id' must be a non-empty string")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("'prompt' must be a non-empty string")
        if not isinstance(media, list) or not all(
            isinstance(item, str) and item.strip() for item in media
        ):
            raise ValueError("'media' must be a list of non-empty strings")
        if not isinstance(expected_keywords, list) or not all(
            isinstance(item, str) and item.strip() for item in expected_keywords
        ):
            raise ValueError("'expected_keywords' must be a list of non-empty strings")
        if not isinstance(metadata, dict):
            raise ValueError("'metadata' must be an object")
        normalized_keywords = tuple(
            item.strip() for item in expected_keywords
        )
        if len(
            {item.casefold() for item in normalized_keywords}
        ) != len(normalized_keywords):
            raise ValueError("'expected_keywords' must not contain duplicates")
        if schema_version != LEGACY_TASK_SCHEMA_VERSION:
            if not isinstance(scoring, dict):
                raise ValueError(
                    f"'scoring' must be an object for schema {schema_version}"
                )
            scoring_config = ScoringConfig.from_mapping(scoring)
        else:
            if scoring is not None:
                raise ValueError(
                    "'scoring' requires schema_version "
                    f"'{STRUCTURED_TASK_SCHEMA_VERSION}' or newer"
                )
            scoring_config = ScoringConfig()

        if (
            scoring_config.type == "numeric_tolerance"
            and schema_version != CURRENT_TASK_SCHEMA_VERSION
        ):
            raise ValueError(
                "'numeric_tolerance' requires schema_version "
                f"'{CURRENT_TASK_SCHEMA_VERSION}'"
            )

        if (
            scoring_config.type in {"normalized_exact_match", "attribute_groups"}
            and not expected_keywords
        ):
            raise ValueError(
                f"'expected_keywords' cannot be empty for '{scoring_config.type}'"
            )
        if (
            scoring_config.type == "attribute_groups"
            and len(expected_keywords) != len(scoring_config.groups)
        ):
            raise ValueError(
                "'expected_keywords' and 'scoring.groups' must have equal length"
            )
        if scoring_config.type == "numeric_tolerance" and expected_keywords:
            raise ValueError(
                "'expected_keywords' must be empty for 'numeric_tolerance'; "
                "use 'scoring.target' as the numeric reference"
            )

        return cls(
            id=task_id.strip(),
            prompt=prompt.strip(),
            schema_version=schema_version,
            media=tuple(item.strip() for item in media),
            expected_keywords=normalized_keywords,
            scoring=scoring_config,
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
    phase: str
    repetition: int
    task_schema_version: str
    dataset_version: str
    task_id: str
    category: str
    backend: str
    model_revision: str
    timestamp_utc: str
    status: str
    response_text: str | None
    latency_ms: float
    score: float | None
    metric_name: str
    metric_details: Mapping[str, Any]
    matched_keywords: tuple[str, ...]
    expected_keywords: tuple[str, ...]
    media: tuple[str, ...]
    usage: Mapping[str, Any]
    error: str | None
    attempt_index: int = 1
    terminal: bool = True
    retryable: bool = False
    cumulative_latency_ms: float | None = None
    timeout_seconds: float | None = None
    max_retries: int = 0

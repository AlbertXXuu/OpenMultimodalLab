"""Benchmark orchestration and append-safe per-task result recording."""

from __future__ import annotations

import json
import math
import os
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Iterable, Mapping

from .adapters.base import ModelAdapter
from .adapters.errors import AdapterError
from .metrics import score_response
from .models import EvaluationTask, RunRecord


RUN_RECORD_SCHEMA_VERSION = "0.4"
RETRYABLE_STATUSES = frozenset({"generation_error", "timeout"})


def _normalize_retry_config(
    max_retries: int,
    timeout_seconds: float | None,
) -> tuple[int, float | None]:
    if (
        not isinstance(max_retries, int)
        or isinstance(max_retries, bool)
        or max_retries < 0
    ):
        raise ValueError("max_retries must be at least 0")
    if timeout_seconds is not None and (
        not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or not math.isfinite(float(timeout_seconds))
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be a finite number above 0")
    return max_retries, (
        float(timeout_seconds) if timeout_seconds is not None else None
    )


class ResumeError(ValueError):
    """Raised when an existing run cannot be resumed without ambiguity."""


def _attempt_plan(
    tasks: list[EvaluationTask],
    *,
    warmup: int,
    repetitions: int,
) -> list[tuple[str, int, EvaluationTask]]:
    attempts: list[tuple[str, int, EvaluationTask]] = []
    if tasks:
        attempts.extend(
            ("warmup", warmup_index, tasks[0])
            for warmup_index in range(1, warmup + 1)
        )
    attempts.extend(
        ("measurement", repetition, task)
        for repetition in range(1, repetitions + 1)
        for task in tasks
    )
    return attempts


def _record_from_mapping(
    value: Mapping[str, Any],
    *,
    line_number: int,
) -> RunRecord:
    converted = dict(value)
    for field_name in ("matched_keywords", "expected_keywords", "media"):
        field_value = converted.get(field_name)
        if not isinstance(field_value, list):
            raise ResumeError(
                f"existing output line {line_number} has invalid "
                f"'{field_name}'"
            )
        converted[field_name] = tuple(field_value)
    try:
        return RunRecord(**converted)
    except TypeError as exc:
        raise ResumeError(
            f"existing output line {line_number} does not match run-record "
            f"schema {RUN_RECORD_SCHEMA_VERSION}: {exc}"
        ) from exc


def _load_resume_records(path: Path) -> list[RunRecord]:
    raw = path.read_bytes()
    if not raw:
        return []
    if not raw.endswith(b"\n"):
        raise ResumeError(
            "existing output does not end at a durable JSONL record boundary"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ResumeError("existing output is not valid UTF-8") from exc

    records: list[RunRecord] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ResumeError(
                f"existing output line {line_number} is unexpectedly empty"
            )
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ResumeError(
                f"existing output line {line_number} is invalid JSON: "
                f"{exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise ResumeError(
                f"existing output line {line_number} must be an object"
            )
        records.append(
            _record_from_mapping(value, line_number=line_number)
        )
    return records


def _validate_resume_prefix(
    records: list[RunRecord],
    attempts: list[tuple[str, int, EvaluationTask]],
    adapter: ModelAdapter,
    *,
    max_retries: int,
    timeout_seconds: float | None,
) -> None:
    if len(records) > len(attempts) * (max_retries + 1):
        raise ResumeError(
            "existing output contains more records than the requested run"
        )

    expected_backend = str(
        getattr(adapter, "name", type(adapter).__name__)
    )
    expected_revision = str(getattr(adapter, "revision", "unknown"))
    plan_index = 0
    expected_attempt_index = 1
    cumulative_latency_ms = 0.0
    for index, record in enumerate(records, start=1):
        if plan_index >= len(attempts):
            raise ResumeError(
                "existing output contains records after the attempt plan completed"
            )
        attempt = attempts[plan_index]
        phase, repetition, task = attempt
        expected_dataset_version = str(
            task.metadata.get("dataset_version", "unspecified")
        )
        expected_category = str(
            task.metadata.get("category", "uncategorized")
        )
        expected_metric = (
            "unscored_warmup"
            if phase == "warmup"
            else task.scoring.type
        )
        mismatches = {
            "schema_version": (
                record.schema_version,
                RUN_RECORD_SCHEMA_VERSION,
            ),
            "phase": (record.phase, phase),
            "repetition": (record.repetition, repetition),
            "task_id": (record.task_id, task.id),
            "task_schema_version": (
                record.task_schema_version,
                task.schema_version,
            ),
            "dataset_version": (
                record.dataset_version,
                expected_dataset_version,
            ),
            "category": (record.category, expected_category),
            "backend": (record.backend, expected_backend),
            "model_revision": (
                record.model_revision,
                expected_revision,
            ),
            "metric_name": (record.metric_name, expected_metric),
            "expected_keywords": (
                record.expected_keywords,
                task.expected_keywords,
            ),
            "media": (record.media, task.media),
            "attempt_index": (
                record.attempt_index,
                expected_attempt_index,
            ),
            "timeout_seconds": (
                record.timeout_seconds,
                timeout_seconds,
            ),
            "max_retries": (record.max_retries, max_retries),
        }
        different = [
            f"{name}={actual!r} (expected {expected!r})"
            for name, (actual, expected) in mismatches.items()
            if actual != expected
        ]
        if different:
            raise ResumeError(
                f"existing output record {index} is not the expected run "
                f"prefix: {'; '.join(different)}"
            )

        if (
            not isinstance(record.attempt_index, int)
            or isinstance(record.attempt_index, bool)
            or record.attempt_index < 1
        ):
            raise ResumeError(
                f"existing output record {index} has invalid attempt_index"
            )
        if not isinstance(record.terminal, bool):
            raise ResumeError(
                f"existing output record {index} has invalid terminal flag"
            )
        if not isinstance(record.retryable, bool):
            raise ResumeError(
                f"existing output record {index} has invalid retryable flag"
            )
        if (
            not isinstance(record.max_retries, int)
            or isinstance(record.max_retries, bool)
            or record.max_retries < 0
        ):
            raise ResumeError(
                f"existing output record {index} has invalid max_retries"
            )
        if record.timeout_seconds is not None and (
            not isinstance(record.timeout_seconds, (int, float))
            or isinstance(record.timeout_seconds, bool)
            or not math.isfinite(float(record.timeout_seconds))
            or record.timeout_seconds <= 0
        ):
            raise ResumeError(
                f"existing output record {index} has invalid timeout_seconds"
            )
        if (
            not isinstance(record.latency_ms, (int, float))
            or isinstance(record.latency_ms, bool)
            or not math.isfinite(float(record.latency_ms))
            or record.latency_ms < 0
        ):
            raise ResumeError(
                f"existing output record {index} has invalid latency_ms"
            )
        expected_cumulative = cumulative_latency_ms + record.latency_ms
        if (
            record.cumulative_latency_ms is None
            or not isinstance(record.cumulative_latency_ms, (int, float))
            or isinstance(record.cumulative_latency_ms, bool)
            or not math.isfinite(float(record.cumulative_latency_ms))
            or not math.isclose(
                record.cumulative_latency_ms,
                expected_cumulative,
                rel_tol=1e-12,
                abs_tol=1e-9,
            )
        ):
            raise ResumeError(
                f"existing output record {index} has invalid "
                "cumulative_latency_ms"
            )
        expected_retryable = record.status in RETRYABLE_STATUSES
        expected_terminal = (
            not expected_retryable
            or record.attempt_index > max_retries
        )
        if record.retryable != expected_retryable:
            raise ResumeError(
                f"existing output record {index} has invalid retryable flag"
            )
        if record.terminal != expected_terminal:
            raise ResumeError(
                f"existing output record {index} has invalid terminal flag"
            )

        if record.terminal:
            plan_index += 1
            expected_attempt_index = 1
            cumulative_latency_ms = 0.0
        else:
            expected_attempt_index += 1
            cumulative_latency_ms = record.cumulative_latency_ms


def validate_resume_output(
    tasks: Iterable[EvaluationTask],
    adapter: ModelAdapter,
    output_path: str | Path,
    *,
    warmup: int = 0,
    repetitions: int = 1,
    max_retries: int = 0,
    timeout_seconds: float | None = None,
) -> list[RunRecord]:
    """Validate and return the durable prefix of an interrupted run."""

    max_retries, timeout_seconds = _normalize_retry_config(
        max_retries,
        timeout_seconds,
    )
    destination = Path(output_path)
    if not destination.is_file():
        raise ResumeError(
            f"cannot resume because output does not exist: {destination}"
        )
    attempts = _attempt_plan(
        list(tasks),
        warmup=warmup,
        repetitions=repetitions,
    )
    records = _load_resume_records(destination)
    _validate_resume_prefix(
        records,
        attempts,
        adapter,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
    return records


def _resume_cursor(
    records: list[RunRecord],
) -> tuple[int, int, float]:
    """Return plan index, next invocation index, and accumulated latency."""

    plan_index = 0
    attempt_index = 1
    cumulative_latency_ms = 0.0
    for record in records:
        if record.terminal:
            plan_index += 1
            attempt_index = 1
            cumulative_latency_ms = 0.0
        else:
            attempt_index = record.attempt_index + 1
            cumulative_latency_ms = record.cumulative_latency_ms or 0.0
    return plan_index, attempt_index, cumulative_latency_ms


def _run_once(
    task: EvaluationTask,
    adapter: ModelAdapter,
    *,
    phase: str,
    repetition: int,
    attempt_index: int,
    max_retries: int,
    timeout_seconds: float | None,
    prior_latency_ms: float,
) -> RunRecord:
    started_at = datetime.now(timezone.utc).isoformat()
    start_ns = perf_counter_ns()
    dataset_version = str(task.metadata.get("dataset_version", "unspecified"))
    category = str(task.metadata.get("category", "uncategorized"))
    metric_name = (
        "unscored_warmup" if phase == "warmup" else task.scoring.type
    )

    try:
        if timeout_seconds is None:
            output = adapter.generate(task)
        else:
            output = adapter.generate(
                task,
                timeout_seconds=timeout_seconds,
            )
    except Exception as exc:  # Adapter boundaries must become durable data.
        latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
        status = (
            exc.status if isinstance(exc, AdapterError) else "generation_error"
        )
        retryable = status in RETRYABLE_STATUSES
        return RunRecord(
            schema_version=RUN_RECORD_SCHEMA_VERSION,
            phase=phase,
            repetition=repetition,
            task_schema_version=task.schema_version,
            dataset_version=dataset_version,
            task_id=task.id,
            category=category,
            backend=getattr(adapter, "name", type(adapter).__name__),
            model_revision=getattr(adapter, "revision", "unknown"),
            timestamp_utc=started_at,
            status=status,
            response_text=None,
            latency_ms=latency_ms,
            score=None,
            metric_name=metric_name,
            metric_details={},
            matched_keywords=(),
            expected_keywords=task.expected_keywords,
            media=task.media,
            usage={},
            error=f"{type(exc).__name__}: {exc}",
            attempt_index=attempt_index,
            terminal=not retryable or attempt_index > max_retries,
            retryable=retryable,
            cumulative_latency_ms=prior_latency_ms + latency_ms,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    if phase == "warmup":
        latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
        return RunRecord(
            schema_version=RUN_RECORD_SCHEMA_VERSION,
            phase=phase,
            repetition=repetition,
            task_schema_version=task.schema_version,
            dataset_version=dataset_version,
            task_id=task.id,
            category=category,
            backend=output.backend,
            model_revision=output.model_revision,
            timestamp_utc=started_at,
            status="success",
            response_text=output.text,
            latency_ms=latency_ms,
            score=None,
            metric_name=metric_name,
            metric_details={},
            matched_keywords=(),
            expected_keywords=task.expected_keywords,
            media=task.media,
            usage=output.usage,
            error=None,
            attempt_index=attempt_index,
            cumulative_latency_ms=prior_latency_ms + latency_ms,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    try:
        metric = score_response(task, output.text)
    except Exception as exc:
        latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
        return RunRecord(
            schema_version=RUN_RECORD_SCHEMA_VERSION,
            phase=phase,
            repetition=repetition,
            task_schema_version=task.schema_version,
            dataset_version=dataset_version,
            task_id=task.id,
            category=category,
            backend=output.backend,
            model_revision=output.model_revision,
            timestamp_utc=started_at,
            status="evaluation_error",
            response_text=output.text,
            latency_ms=latency_ms,
            score=None,
            metric_name=task.scoring.type,
            metric_details={},
            matched_keywords=(),
            expected_keywords=task.expected_keywords,
            media=task.media,
            usage=output.usage,
            error=f"{type(exc).__name__}: {exc}",
            attempt_index=attempt_index,
            cumulative_latency_ms=prior_latency_ms + latency_ms,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
    return RunRecord(
        schema_version=RUN_RECORD_SCHEMA_VERSION,
        phase=phase,
        repetition=repetition,
        task_schema_version=task.schema_version,
        dataset_version=dataset_version,
        task_id=task.id,
        category=category,
        backend=output.backend,
        model_revision=output.model_revision,
        timestamp_utc=started_at,
        status="success",
        response_text=output.text,
        latency_ms=latency_ms,
        score=metric.score,
        metric_name=metric.name,
        metric_details=metric.details,
        matched_keywords=metric.matched,
        expected_keywords=task.expected_keywords,
        media=task.media,
        usage=output.usage,
        error=None,
        attempt_index=attempt_index,
        cumulative_latency_ms=prior_latency_ms + latency_ms,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def run_benchmark(
    tasks: Iterable[EvaluationTask],
    adapter: ModelAdapter,
    output_path: str | Path,
    *,
    warmup: int = 0,
    repetitions: int = 1,
    max_retries: int = 0,
    timeout_seconds: float | None = None,
    resume: bool = False,
    on_record_persisted: (
        Callable[[tuple[RunRecord, ...]], None] | None
    ) = None,
) -> list[RunRecord]:
    """Run or strictly resume a benchmark, persisting every attempt."""

    if warmup < 0:
        raise ValueError("warmup must be at least 0")
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    max_retries, timeout_seconds = _normalize_retry_config(
        max_retries,
        timeout_seconds,
    )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    task_list = list(tasks)
    attempts = _attempt_plan(
        task_list,
        warmup=warmup,
        repetitions=repetitions,
    )
    if resume:
        records = validate_resume_output(
            task_list,
            adapter,
            destination,
            warmup=warmup,
            repetitions=repetitions,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        mode = "a"
    else:
        records = []
        mode = "w"

    plan_index, attempt_index, cumulative_latency_ms = _resume_cursor(records)

    with destination.open(mode, encoding="utf-8", newline="\n") as handle:
        while plan_index < len(attempts):
            phase, repetition, task = attempts[plan_index]
            record = _run_once(
                task,
                adapter,
                phase=phase,
                repetition=repetition,
                attempt_index=attempt_index,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds,
                prior_latency_ms=cumulative_latency_ms,
            )
            records.append(record)
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            if on_record_persisted is not None:
                on_record_persisted(tuple(records))
            if record.terminal:
                plan_index += 1
                attempt_index = 1
                cumulative_latency_ms = 0.0
            else:
                attempt_index += 1
                cumulative_latency_ms = record.cumulative_latency_ms or 0.0

    return records

"""Benchmark orchestration and append-safe per-task result recording."""

from __future__ import annotations

import json
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


RUN_RECORD_SCHEMA_VERSION = "0.3"


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
) -> None:
    if len(records) > len(attempts):
        raise ResumeError(
            "existing output contains more records than the requested run"
        )

    expected_backend = str(
        getattr(adapter, "name", type(adapter).__name__)
    )
    expected_revision = str(getattr(adapter, "revision", "unknown"))
    for index, (record, attempt) in enumerate(
        zip(records, attempts, strict=False),
        start=1,
    ):
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


def validate_resume_output(
    tasks: Iterable[EvaluationTask],
    adapter: ModelAdapter,
    output_path: str | Path,
    *,
    warmup: int = 0,
    repetitions: int = 1,
) -> list[RunRecord]:
    """Validate and return the durable prefix of an interrupted run."""

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
    _validate_resume_prefix(records, attempts, adapter)
    return records


def _run_once(
    task: EvaluationTask,
    adapter: ModelAdapter,
    *,
    phase: str,
    repetition: int,
) -> RunRecord:
    started_at = datetime.now(timezone.utc).isoformat()
    start_ns = perf_counter_ns()
    dataset_version = str(task.metadata.get("dataset_version", "unspecified"))
    category = str(task.metadata.get("category", "uncategorized"))
    metric_name = (
        "unscored_warmup" if phase == "warmup" else task.scoring.type
    )

    try:
        output = adapter.generate(task)
    except Exception as exc:  # Adapter boundaries must become durable data.
        latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
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
            status=(
                exc.status if isinstance(exc, AdapterError) else "generation_error"
            ),
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
    )


def run_benchmark(
    tasks: Iterable[EvaluationTask],
    adapter: ModelAdapter,
    output_path: str | Path,
    *,
    warmup: int = 0,
    repetitions: int = 1,
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
        )
        mode = "a"
    else:
        records = []
        mode = "w"

    with destination.open(mode, encoding="utf-8", newline="\n") as handle:
        for phase, repetition, task in attempts[len(records) :]:
            record = _run_once(
                task,
                adapter,
                phase=phase,
                repetition=repetition,
            )
            records.append(record)
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            if on_record_persisted is not None:
                on_record_persisted(tuple(records))

    return records

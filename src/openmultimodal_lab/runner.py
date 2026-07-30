"""Benchmark orchestration and append-safe per-task result recording."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from typing import Iterable

from .adapters.base import ModelAdapter
from .adapters.errors import AdapterError
from .metrics import score_response
from .models import EvaluationTask, RunRecord


RUN_RECORD_SCHEMA_VERSION = "0.3"


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
) -> list[RunRecord]:
    """Run warm-up and measured repetitions, persisting every attempt."""

    if warmup < 0:
        raise ValueError("warmup must be at least 0")
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    task_list = list(tasks)
    records: list[RunRecord] = []

    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for warmup_index in range(1, warmup + 1):
            if not task_list:
                break
            record = _run_once(
                task_list[0],
                adapter,
                phase="warmup",
                repetition=warmup_index,
            )
            records.append(record)
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            handle.flush()

        for repetition in range(1, repetitions + 1):
            for task in task_list:
                record = _run_once(
                    task,
                    adapter,
                    phase="measurement",
                    repetition=repetition,
                )
                records.append(record)
                handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
                handle.flush()

    return records

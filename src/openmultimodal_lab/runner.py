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


def run_benchmark(
    tasks: Iterable[EvaluationTask],
    adapter: ModelAdapter,
    output_path: str | Path,
) -> list[RunRecord]:
    """Run tasks sequentially and write one JSON record after every task."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    records: list[RunRecord] = []

    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for task in tasks:
            started_at = datetime.now(timezone.utc).isoformat()
            start_ns = perf_counter_ns()

            try:
                output = adapter.generate(task)
            except Exception as exc:  # Adapter boundaries must become durable data.
                latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
                record = RunRecord(
                    schema_version="0.2",
                    task_schema_version=task.schema_version,
                    dataset_version=str(
                        task.metadata.get("dataset_version", "unspecified")
                    ),
                    task_id=task.id,
                    category=str(task.metadata.get("category", "uncategorized")),
                    backend=getattr(adapter, "name", type(adapter).__name__),
                    model_revision=getattr(adapter, "revision", "unknown"),
                    timestamp_utc=started_at,
                    status=(
                        exc.status
                        if isinstance(exc, AdapterError)
                        else "generation_error"
                    ),
                    response_text=None,
                    latency_ms=latency_ms,
                    score=None,
                    metric_name=task.scoring.type,
                    metric_details={},
                    matched_keywords=(),
                    expected_keywords=task.expected_keywords,
                    media=task.media,
                    usage={},
                    error=f"{type(exc).__name__}: {exc}",
                )
            else:
                try:
                    metric = score_response(task, output.text)
                except Exception as exc:
                    latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
                    record = RunRecord(
                        schema_version="0.2",
                        task_schema_version=task.schema_version,
                        dataset_version=str(
                            task.metadata.get("dataset_version", "unspecified")
                        ),
                        task_id=task.id,
                        category=str(
                            task.metadata.get("category", "uncategorized")
                        ),
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
                else:
                    latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
                    record = RunRecord(
                        schema_version="0.2",
                        task_schema_version=task.schema_version,
                        dataset_version=str(
                            task.metadata.get("dataset_version", "unspecified")
                        ),
                        task_id=task.id,
                        category=str(
                            task.metadata.get("category", "uncategorized")
                        ),
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

            records.append(record)
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            handle.flush()

    return records

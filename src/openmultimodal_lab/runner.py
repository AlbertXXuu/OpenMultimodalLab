"""Benchmark orchestration and append-safe per-task result recording."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from typing import Iterable

from .adapters.base import ModelAdapter
from .metrics import keyword_score
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
                latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
                metric = keyword_score(output.text, task.expected_keywords)
                record = RunRecord(
                    schema_version="0.1",
                    task_id=task.id,
                    category=str(task.metadata.get("category", "uncategorized")),
                    backend=output.backend,
                    model_revision=output.model_revision,
                    timestamp_utc=started_at,
                    status="success",
                    response_text=output.text,
                    latency_ms=latency_ms,
                    score=metric.score,
                    matched_keywords=metric.matched,
                    expected_keywords=task.expected_keywords,
                    media=task.media,
                    usage=output.usage,
                    error=None,
                )
            except Exception as exc:  # Adapter boundaries must become data, not lost runs.
                latency_ms = (perf_counter_ns() - start_ns) / 1_000_000
                record = RunRecord(
                    schema_version="0.1",
                    task_id=task.id,
                    category=str(task.metadata.get("category", "uncategorized")),
                    backend=getattr(adapter, "name", type(adapter).__name__),
                    model_revision="unknown",
                    timestamp_utc=started_at,
                    status="generation_error",
                    response_text=None,
                    latency_ms=latency_ms,
                    score=None,
                    matched_keywords=(),
                    expected_keywords=task.expected_keywords,
                    media=task.media,
                    usage={},
                    error=f"{type(exc).__name__}: {exc}",
                )

            records.append(record)
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            handle.flush()

    return records

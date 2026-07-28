"""Rebuild aggregate summaries from raw JSONL run records."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class ReportError(ValueError):
    """Raised when raw run records cannot be summarized."""


def load_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.is_file():
        raise ReportError(f"Run record file does not exist: {source}")

    records: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReportError(
                    f"{source}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise ReportError(f"{source}:{line_number}: record must be an object")
            records.append(value)

    if not records:
        raise ReportError(f"Run record file contains no records: {source}")
    return records


def _nearest_rank_percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    successful = sum(record.get("status") == "success" for record in records)
    scores = [
        float(record["score"])
        for record in records
        if isinstance(record.get("score"), (int, float))
    ]
    latencies = [
        float(record["latency_ms"])
        for record in records
        if isinstance(record.get("latency_ms"), (int, float))
    ]
    failures: dict[str, int] = {}
    for record in records:
        status = str(record.get("status", "unknown"))
        if status != "success":
            failures[status] = failures.get(status, 0) + 1

    return {
        "total_tasks": total,
        "successful_tasks": successful,
        "success_rate": successful / total,
        "scored_tasks": len(scores),
        "mean_score": sum(scores) / len(scores) if scores else None,
        "mean_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "p95_latency_ms": _nearest_rank_percentile(latencies, 0.95),
        "failures": failures,
    }


def format_summary(summary: dict[str, Any]) -> str:
    def display_number(value: Any, digits: int = 3) -> str:
        return "n/a" if value is None else f"{float(value):.{digits}f}"

    lines = [
        "OpenMultimodalLab run summary",
        f"Tasks: {summary['total_tasks']}",
        f"Successful: {summary['successful_tasks']}",
        f"Success rate: {display_number(summary['success_rate'] * 100, 1)}%",
        f"Scored tasks: {summary['scored_tasks']}",
        f"Mean score: {display_number(summary['mean_score'])}",
        f"Mean latency: {display_number(summary['mean_latency_ms'])} ms",
        f"P95 latency: {display_number(summary['p95_latency_ms'])} ms",
        f"Failures: {json.dumps(summary['failures'], ensure_ascii=False, sort_keys=True)}",
    ]
    return "\n".join(lines)

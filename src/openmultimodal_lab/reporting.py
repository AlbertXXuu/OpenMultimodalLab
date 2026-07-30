"""Rebuild aggregate summaries from raw JSONL run records."""

from __future__ import annotations

import json
import math
import statistics
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
    warmup_records = [
        record for record in records if record.get("phase") == "warmup"
    ]
    measurement_records = [
        record for record in records if record.get("phase") != "warmup"
    ]
    total = len(measurement_records)
    successful = sum(
        record.get("status") == "success" for record in measurement_records
    )
    scores = [
        float(record["score"])
        for record in measurement_records
        if isinstance(record.get("score"), (int, float))
    ]
    latencies = [
        float(record["latency_ms"])
        for record in measurement_records
        if isinstance(record.get("latency_ms"), (int, float))
    ]
    failures: dict[str, int] = {}
    for record in measurement_records:
        status = str(record.get("status", "unknown"))
        if status != "success":
            failures[status] = failures.get(status, 0) + 1

    def usage_values(
        key: str,
        source_records: list[dict[str, Any]] | None = None,
    ) -> list[float]:
        values: list[float] = []
        for record in (
            measurement_records if source_records is None else source_records
        ):
            usage = record.get("usage")
            if not isinstance(usage, dict):
                continue
            value = usage.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))
        return values

    ttft_values = usage_values("ttft_ms")
    preprocessing_values = usage_values("preprocessing_ms")
    generation_values = usage_values("generation_ms")
    throughput_values = usage_values("output_tokens_per_second")
    decode_throughput_values = usage_values("decode_tokens_per_second")
    peak_memory_values = usage_values("peak_gpu_memory_mb")
    warmup_model_load_values = usage_values(
        "model_load_ms",
        warmup_records,
    )
    repetitions = {
        int(record.get("repetition", 1))
        for record in measurement_records
        if isinstance(record.get("repetition", 1), int)
    }
    successful_measurements = [
        record
        for record in measurement_records
        if record.get("status") == "success"
    ]
    required_performance_fields = (
        "preprocessing_ms",
        "ttft_ms",
        "generation_ms",
        "output_tokens_per_second",
        "peak_gpu_memory_mb",
    )
    performance_metrics_complete = bool(successful_measurements) and all(
        isinstance(record.get("usage"), dict)
        and all(
            isinstance(record["usage"].get(field), (int, float))
            and not isinstance(record["usage"].get(field), bool)
            for field in required_performance_fields
        )
        for record in successful_measurements
    )
    successful_warmups = sum(
        record.get("status") == "success" for record in warmup_records
    )
    formal_performance_run = (
        successful_warmups >= 1
        and len(repetitions) >= 3
        and performance_metrics_complete
    )

    return {
        "total_records": len(records),
        "warmup_attempts": len(warmup_records),
        "total_tasks": total,
        "unique_tasks": len(
            {
                str(record.get("task_id"))
                for record in measurement_records
                if record.get("task_id") is not None
            }
        ),
        "repetitions": len(repetitions) if repetitions else 0,
        "performance_metrics_complete": performance_metrics_complete,
        "formal_performance_run": formal_performance_run,
        "successful_tasks": successful,
        "success_rate": successful / total if total else 0.0,
        "scored_tasks": len(scores),
        "mean_score": sum(scores) / len(scores) if scores else None,
        "median_score": statistics.median(scores) if scores else None,
        "mean_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "median_latency_ms": statistics.median(latencies) if latencies else None,
        "p95_latency_ms": _nearest_rank_percentile(latencies, 0.95),
        "median_preprocessing_ms": (
            statistics.median(preprocessing_values)
            if preprocessing_values
            else None
        ),
        "model_load_ms": (
            max(warmup_model_load_values) if warmup_model_load_values else None
        ),
        "median_ttft_ms": (
            statistics.median(ttft_values) if ttft_values else None
        ),
        "p95_ttft_ms": _nearest_rank_percentile(ttft_values, 0.95),
        "median_generation_ms": (
            statistics.median(generation_values) if generation_values else None
        ),
        "median_output_tokens_per_second": (
            statistics.median(throughput_values) if throughput_values else None
        ),
        "median_decode_tokens_per_second": (
            statistics.median(decode_throughput_values)
            if decode_throughput_values
            else None
        ),
        "peak_gpu_memory_mb": (
            max(peak_memory_values) if peak_memory_values else None
        ),
        "failures": failures,
    }


def format_summary(summary: dict[str, Any]) -> str:
    def display_number(value: Any, digits: int = 3) -> str:
        return "n/a" if value is None else f"{float(value):.{digits}f}"

    lines = [
        "OpenMultimodalLab run summary",
        f"Records: {summary['total_records']}",
        f"Warm-up attempts: {summary['warmup_attempts']}",
        f"Measurement attempts: {summary['total_tasks']}",
        f"Unique tasks: {summary['unique_tasks']}",
        f"Repetitions: {summary['repetitions']}",
        f"Formal performance protocol: "
        f"{'yes' if summary['formal_performance_run'] else 'no'}",
        f"Successful measurements: {summary['successful_tasks']}",
        f"Success rate: {display_number(summary['success_rate'] * 100, 1)}%",
        f"Scored measurements: {summary['scored_tasks']}",
        f"Mean score: {display_number(summary['mean_score'])}",
        f"Median score: {display_number(summary['median_score'])}",
        f"Mean latency: {display_number(summary['mean_latency_ms'])} ms",
        f"Median latency: {display_number(summary['median_latency_ms'])} ms",
        f"P95 latency: {display_number(summary['p95_latency_ms'])} ms",
        f"Median preprocessing: "
        f"{display_number(summary['median_preprocessing_ms'])} ms",
        f"Warm-up model load: {display_number(summary['model_load_ms'])} ms",
        f"Median TTFT: {display_number(summary['median_ttft_ms'])} ms",
        f"P95 TTFT: {display_number(summary['p95_ttft_ms'])} ms",
        f"Median generation: "
        f"{display_number(summary['median_generation_ms'])} ms",
        f"Median output throughput: "
        f"{display_number(summary['median_output_tokens_per_second'])} tok/s",
        f"Median decode throughput: "
        f"{display_number(summary['median_decode_tokens_per_second'])} tok/s",
        f"Peak GPU memory: "
        f"{display_number(summary['peak_gpu_memory_mb'])} MiB",
        f"Failures: {json.dumps(summary['failures'], ensure_ascii=False, sort_keys=True)}",
    ]
    return "\n".join(lines)

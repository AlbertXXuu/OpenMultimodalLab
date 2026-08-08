"""Rebuild aggregate summaries from raw JSONL run records."""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .privacy import portable_path_reference


MAX_RESULT_FILE_BYTES = 256 * 1024 * 1024
MAX_RESULT_LINE_BYTES = 4 * 1024 * 1024
PERFORMANCE_FIELDS = (
    "preprocessing_ms",
    "ttft_ms",
    "generation_ms",
    "output_tokens_per_second",
    "peak_gpu_memory_mb",
)


class ReportError(ValueError):
    """Raised when raw run records cannot be summarized."""


@dataclass(frozen=True, slots=True)
class FormalRunValidation:
    """Machine-checkable result of the documented formal-run protocol."""

    passed: bool
    warmup_attempts: int
    measurement_attempts: int
    repetitions: tuple[int, ...]
    successful_measurements: int
    failed_measurements: int
    complete_repeat_grid: bool
    retry_attempts: int
    measurement_model_reloads: int
    issues: tuple[str, ...]

    @property
    def detail(self) -> str:
        """Return a compact evidence string for readiness checks."""

        return (
            f"warmups={self.warmup_attempts}, "
            f"measurements={self.measurement_attempts}, "
            f"repetitions={len(self.repetitions)}, "
            f"successful={self.successful_measurements}, "
            f"failures={self.failed_measurements}, "
            f"complete_grid={self.complete_repeat_grid}, "
            f"retries={self.retry_attempts}, "
            f"measurement_reloads={self.measurement_model_reloads}"
        )


def load_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    source_label = portable_path_reference(str(source))
    if not source.is_file():
        raise ReportError(f"Run record file does not exist: {source_label}")
    if source.stat().st_size > MAX_RESULT_FILE_BYTES:
        raise ReportError(
            f"Run record file exceeds the "
            f"{MAX_RESULT_FILE_BYTES // (1024 * 1024)} MiB safety limit: "
            f"{source_label}"
        )

    records: list[dict[str, Any]] = []
    total_bytes = 0
    with source.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            total_bytes += len(raw_line)
            if total_bytes > MAX_RESULT_FILE_BYTES:
                raise ReportError(
                    f"Run record file exceeds the "
                    f"{MAX_RESULT_FILE_BYTES // (1024 * 1024)} MiB safety "
                    f"limit: {source_label}"
                )
            if len(raw_line) > MAX_RESULT_LINE_BYTES:
                raise ReportError(
                    f"{source_label}:{line_number}: record exceeds the "
                    f"{MAX_RESULT_LINE_BYTES // (1024 * 1024)} MiB "
                    "line safety limit"
                )
            try:
                line = raw_line.decode("utf-8").strip()
            except UnicodeDecodeError as exc:
                raise ReportError(
                    f"{source_label}:{line_number}: record is not valid UTF-8"
                ) from exc
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReportError(
                    f"{source_label}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise ReportError(
                    f"{source_label}:{line_number}: record must be an object"
                )
            records.append(value)

    if not records:
        raise ReportError(
            f"Run record file contains no records: {source_label}"
        )
    return records


def _nearest_rank_percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def validate_formal_run(
    records: list[dict[str, Any]],
) -> FormalRunValidation:
    """Validate exactly one warm-up and a complete three-repeat task grid."""

    terminal_records = [
        record for record in records if record.get("terminal", True)
    ]
    warmup_records = [
        record
        for record in terminal_records
        if record.get("phase") == "warmup"
    ]
    measurement_records = [
        record
        for record in terminal_records
        if record.get("phase") == "measurement"
    ]
    unrecognized_phases = [
        record
        for record in terminal_records
        if record.get("phase") not in {"warmup", "measurement"}
    ]
    retry_attempts = len(records) - len(terminal_records)

    raw_repetition_values = [
        record.get("repetition") for record in measurement_records
    ]
    valid_repetitions = all(
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
        for value in raw_repetition_values
    )
    repetitions: tuple[int, ...] = (
        tuple(
            sorted(
                {cast(int, value) for value in raw_repetition_values}
            )
        )
        if valid_repetitions
        else ()
    )

    successful = [
        record
        for record in measurement_records
        if record.get("status") == "success"
    ]
    failures = [
        record
        for record in measurement_records
        if record.get("status") != "success"
    ]
    complete_metrics = bool(successful) and all(
        isinstance(record.get("usage"), dict)
        and all(
            isinstance(record["usage"].get(field), (int, float))
            and not isinstance(record["usage"].get(field), bool)
            for field in PERFORMANCE_FIELDS
        )
        for record in successful
    )
    complete_failures = all(
        isinstance(record.get("status"), str)
        and bool(record["status"].strip())
        and isinstance(record.get("error"), str)
        and bool(record["error"].strip())
        for record in failures
    )

    tasks_by_repetition: dict[object, list[object]] = {}
    for record in measurement_records:
        tasks_by_repetition.setdefault(record.get("repetition"), []).append(
            record.get("task_id")
        )
    valid_task_ids = all(
        isinstance(task_id, str) and bool(task_id.strip())
        for task_ids in tasks_by_repetition.values()
        for task_id in task_ids
    )
    no_duplicate_cells = all(
        len(task_ids) == len(set(task_ids))
        for task_ids in tasks_by_repetition.values()
    )
    complete_repeat_grid = (
        bool(tasks_by_repetition)
        and valid_task_ids
        and no_duplicate_cells
        and len(
            {
                frozenset(task_ids)
                for task_ids in tasks_by_repetition.values()
            }
        )
        == 1
    )
    measurement_model_reloads = sum(
        isinstance(record.get("usage"), dict)
        and isinstance(
            record["usage"].get("model_load_ms"),
            (int, float),
        )
        and not isinstance(record["usage"].get("model_load_ms"), bool)
        and record["usage"]["model_load_ms"] > 0
        for record in measurement_records
    )

    issues: list[str] = []
    if len(warmup_records) != 1:
        issues.append("expected exactly one warm-up record")
    elif warmup_records[0].get("status") != "success":
        issues.append("warm-up record did not succeed")
    if unrecognized_phases:
        issues.append("terminal records contain an unrecognized phase")
    if repetitions != (1, 2, 3):
        issues.append("measurement repetitions must be exactly 1, 2, and 3")
    if not successful:
        issues.append("run contains no successful measurements")
    if not complete_metrics:
        issues.append("successful measurements lack required performance metrics")
    if not complete_failures:
        issues.append("failed measurements lack a status or error message")
    if not complete_repeat_grid:
        issues.append("measurement records do not form a complete task grid")
    if retry_attempts:
        issues.append("formal run contains retry-attempt records")
    if measurement_model_reloads:
        issues.append("model was loaded during a measurement attempt")

    return FormalRunValidation(
        passed=not issues,
        warmup_attempts=len(warmup_records),
        measurement_attempts=len(measurement_records),
        repetitions=repetitions,
        successful_measurements=len(successful),
        failed_measurements=len(failures),
        complete_repeat_grid=complete_repeat_grid,
        retry_attempts=retry_attempts,
        measurement_model_reloads=measurement_model_reloads,
        issues=tuple(issues),
    )


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    terminal_records = [
        record for record in records if record.get("terminal", True)
    ]
    warmup_records = [
        record
        for record in terminal_records
        if record.get("phase") == "warmup"
    ]
    measurement_records = [
        record
        for record in terminal_records
        if record.get("phase") != "warmup"
    ]
    retry_attempts = len(records) - len(terminal_records)
    timeout_invocations = sum(
        record.get("status") == "timeout" for record in records
    )
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
        float(record.get("cumulative_latency_ms") or record["latency_ms"])
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
    measurement_model_load_values = usage_values("model_load_ms")
    measurement_model_reloads = sum(
        value > 0 for value in measurement_model_load_values
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
    performance_metrics_complete = bool(successful_measurements) and all(
        isinstance(record.get("usage"), dict)
        and all(
            isinstance(record["usage"].get(field), (int, float))
            and not isinstance(record["usage"].get(field), bool)
            for field in PERFORMANCE_FIELDS
        )
        for record in successful_measurements
    )
    formal_validation = validate_formal_run(records)

    return {
        "total_records": len(records),
        "generation_invocations": len(records),
        "retry_attempts": retry_attempts,
        "timeout_invocations": timeout_invocations,
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
        "measurement_model_reloads": measurement_model_reloads,
        "formal_performance_run": formal_validation.passed,
        "formal_protocol_issues": list(formal_validation.issues),
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
        f"Generation invocations: {summary['generation_invocations']}",
        f"Retry attempts: {summary['retry_attempts']}",
        f"Timeout invocations: {summary['timeout_invocations']}",
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
        f"Measurement model reloads: {summary['measurement_model_reloads']}",
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

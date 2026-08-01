"""Build deterministic, auditable report bundles from formal run records."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .privacy import redact_local_paths
from .reporting import ReportError, load_records, summarize, validate_formal_run


MAX_MANIFEST_BYTES = 4 * 1024 * 1024
BUNDLE_FILENAMES = (
    "report.md",
    "run-summary.csv",
    "category-summary.csv",
    "failures.csv",
    "overview.svg",
    "build-manifest.json",
)


@dataclass(frozen=True, slots=True)
class FormalSource:
    """One verified result/manifest pair used by a report bundle."""

    result_path: Path
    manifest_path: Path
    result_reference: str
    manifest_reference: str
    result_sha256: str
    manifest_sha256: str
    dataset_sha256: str
    dataset_reference: str
    dataset_versions: tuple[str, ...]
    task_ids: tuple[str, ...]
    backend: str
    model_id: str
    model_revision: str
    git_commit: str
    records: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]
    summary: dict[str, Any]

    @property
    def dataset_label(self) -> str:
        """Return the version labels represented by this result file."""

        return ", ".join(self.dataset_versions)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _project_reference(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise ReportError(
            f"Report inputs must be inside the project root: {path.name}"
        ) from exc


def _project_artifact(project_root: Path, reference: object) -> Path:
    if not isinstance(reference, str) or not reference.strip():
        raise ReportError("Manifest contains an invalid project-relative path")
    candidate = Path(reference)
    if candidate.is_absolute():
        raise ReportError("Manifest artifact path must be project-relative")
    resolved = (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ReportError("Manifest artifact path leaves the project root") from exc
    return resolved


def _read_manifest(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise ReportError(f"Run manifest does not exist: {path.name}")
    with path.open("rb") as handle:
        raw = handle.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ReportError("Run manifest exceeds the 4 MiB safety limit")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ReportError(f"Run manifest is not valid UTF-8 JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise ReportError(f"Run manifest must contain a JSON object: {path.name}")
    return value, raw


def _string_set(records: Iterable[dict[str, Any]], key: str) -> set[str]:
    values: set[str] = set()
    for record in records:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            values.add(value)
    return values


def _model_ids(records: Iterable[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
    for record in records:
        usage = record.get("usage")
        if not isinstance(usage, dict):
            continue
        value = usage.get("model_id")
        if isinstance(value, str) and value.strip():
            values.add(value)
    return values


def _single_value(values: set[str], field: str, issues: list[str]) -> str:
    if len(values) != 1:
        issues.append(f"records must contain exactly one {field}")
        return ""
    return next(iter(values))


def _manifest_value(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, dict) else None


def load_formal_source(
    result_path: str | Path,
    *,
    project_root: str | Path,
) -> FormalSource:
    """Load and cross-check one formal result with its sidecar manifest."""

    root = Path(project_root).resolve()
    result = Path(result_path).resolve()
    result_reference = _project_reference(result, root)
    if result.suffix.casefold() != ".jsonl":
        raise ReportError(f"Formal result must use a .jsonl suffix: {result.name}")
    manifest_path = result.with_suffix(".manifest.json")
    manifest_reference = _project_reference(manifest_path, root)
    records = load_records(result)
    manifest, manifest_bytes = _read_manifest(manifest_path)
    result_bytes = result.read_bytes()
    result_sha256 = _sha256_bytes(result_bytes)
    manifest_sha256 = _sha256_bytes(manifest_bytes)
    formal = validate_formal_run(records)
    issues = list(formal.issues)

    terminal = [record for record in records if record.get("terminal", True)]
    measurements = [
        record for record in terminal if record.get("phase") == "measurement"
    ]
    backend = _single_value(_string_set(terminal, "backend"), "backend", issues)
    model_revision = _single_value(
        _string_set(terminal, "model_revision"),
        "model revision",
        issues,
    )
    model_id = _single_value(_model_ids(terminal), "model identifier", issues)
    dataset_versions = tuple(sorted(_string_set(measurements, "dataset_version")))
    if not dataset_versions:
        issues.append("measurement records contain no dataset version")
    task_ids = tuple(sorted(_string_set(measurements, "task_id")))

    manifest_backend = manifest.get("backend")
    manifest_dataset = manifest.get("dataset")
    manifest_output = manifest.get("output")
    manifest_protocol = manifest.get("protocol")
    manifest_generation = manifest.get("generation")
    manifest_environment = manifest.get("environment")
    manifest_git = _manifest_value(manifest_environment, "git")

    if manifest.get("schema_version") != "1.0":
        issues.append("manifest schema_version must be 1.0")
    if manifest.get("status") != "completed":
        issues.append("manifest status must be completed")
    if manifest.get("records_written") != len(records):
        issues.append("manifest records_written does not match JSONL")
    if manifest.get("measurement_records") != len(measurements):
        issues.append("manifest measurement_records does not match JSONL")
    if manifest.get("warmup_records") != formal.warmup_attempts:
        issues.append("manifest warmup_records does not match JSONL")
    if manifest.get("retry_records") not in {None, 0}:
        issues.append("manifest retry_records must be zero")
    output_sha256 = _manifest_value(manifest_output, "sha256")
    if output_sha256 is not None and output_sha256 != result_sha256:
        issues.append("manifest output hash does not match JSONL")
    output_size = _manifest_value(manifest_output, "size_bytes")
    if output_size is not None and output_size != len(result_bytes):
        issues.append("manifest output size does not match JSONL")
    if _manifest_value(manifest_backend, "name") != backend:
        issues.append("manifest backend name does not match JSONL")
    if _manifest_value(manifest_backend, "model_id") != model_id:
        issues.append("manifest model identifier does not match JSONL")
    if _manifest_value(manifest_backend, "model_revision") != model_revision:
        issues.append("manifest model revision does not match JSONL")
    if _manifest_value(manifest_protocol, "warmup_attempts") != 1:
        issues.append("manifest protocol must declare one warm-up")
    if _manifest_value(manifest_protocol, "repetitions") != 3:
        issues.append("manifest protocol must declare three repetitions")
    max_retries = _manifest_value(manifest_protocol, "max_retries")
    if max_retries not in {None, 0}:
        issues.append("manifest protocol must disable retries")
    if _manifest_value(manifest_generation, "batch_size") != 1:
        issues.append("manifest generation batch size must be one")
    if _manifest_value(manifest_generation, "do_sample") is not False:
        issues.append("manifest generation must disable sampling")
    if _manifest_value(manifest_git, "dirty") is not False:
        issues.append("manifest must record a clean Git worktree")
    git_commit = _manifest_value(manifest_git, "commit")
    if (
        not isinstance(git_commit, str)
        or len(git_commit) != 40
        or any(character not in "0123456789abcdef" for character in git_commit)
    ):
        issues.append("manifest must record a full Git commit")
        git_commit = ""

    manifest_versions = _manifest_value(manifest_dataset, "versions")
    if (
        not isinstance(manifest_versions, list)
        or not all(isinstance(value, str) for value in manifest_versions)
        or sorted(manifest_versions) != list(dataset_versions)
    ):
        issues.append("manifest dataset versions do not match JSONL")
    manifest_task_ids = _manifest_value(manifest_dataset, "task_ids")
    if (
        not isinstance(manifest_task_ids, list)
        or not all(isinstance(value, str) for value in manifest_task_ids)
        or sorted(manifest_task_ids) != list(task_ids)
    ):
        issues.append("manifest task IDs do not match JSONL")
    dataset_sha256 = _manifest_value(manifest_dataset, "sha256")
    if (
        not isinstance(dataset_sha256, str)
        or len(dataset_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in dataset_sha256
        )
    ):
        issues.append("manifest dataset SHA-256 is invalid")
        dataset_sha256 = ""
    dataset_reference = _manifest_value(manifest_dataset, "path")
    if not isinstance(dataset_reference, str):
        issues.append("manifest dataset path is invalid")
        dataset_reference = ""
    else:
        dataset_path = _project_artifact(root, dataset_reference)
        if not dataset_path.is_file():
            issues.append("manifest dataset file is missing")
        elif _sha256_path(dataset_path) != dataset_sha256:
            issues.append("manifest dataset hash does not match the repository")

    media = _manifest_value(manifest_dataset, "media")
    if not isinstance(media, list):
        issues.append("manifest media inventory is invalid")
    else:
        for item in media:
            media_reference = _manifest_value(item, "path")
            media_sha256 = _manifest_value(item, "sha256")
            try:
                media_path = _project_artifact(root, media_reference)
            except ReportError as exc:
                issues.append(str(exc))
                continue
            if not media_path.is_file():
                issues.append(f"manifest media file is missing: {media_path.name}")
            elif _sha256_path(media_path) != media_sha256:
                issues.append(f"manifest media hash mismatch: {media_path.name}")

    if issues:
        unique_issues = "; ".join(dict.fromkeys(issues))
        raise ReportError(f"Formal source rejected ({result.name}): {unique_issues}")

    return FormalSource(
        result_path=result,
        manifest_path=manifest_path,
        result_reference=result_reference,
        manifest_reference=manifest_reference,
        result_sha256=result_sha256,
        manifest_sha256=manifest_sha256,
        dataset_sha256=dataset_sha256,
        dataset_reference=dataset_reference,
        dataset_versions=dataset_versions,
        task_ids=task_ids,
        backend=backend,
        model_id=model_id,
        model_revision=model_revision,
        git_commit=git_commit,
        records=tuple(records),
        manifest=manifest,
        summary=summarize(records),
    )


def load_comparable_sources(
    result_paths: Iterable[str | Path],
    *,
    project_root: str | Path,
) -> tuple[FormalSource, ...]:
    """Load formal sources and require comparable two-backend task grids."""

    paths = [Path(path).resolve() for path in result_paths]
    if len(paths) < 2:
        raise ReportError("A comparison report requires at least two result files")
    if len(paths) != len(set(paths)):
        raise ReportError("Duplicate result paths are not allowed")
    sources = [
        load_formal_source(path, project_root=project_root) for path in paths
    ]
    if len({source.backend for source in sources}) < 2:
        raise ReportError("A comparison report requires at least two backends")

    backend_models: dict[str, tuple[str, str]] = {}
    for source in sources:
        identity = (source.model_id, source.model_revision)
        previous = backend_models.setdefault(source.backend, identity)
        if previous != identity:
            raise ReportError(
                f"Backend {source.backend} changes model identity across inputs"
            )

    by_dataset: dict[str, list[FormalSource]] = {}
    for source in sources:
        by_dataset.setdefault(source.dataset_sha256, []).append(source)
    for dataset_sources in by_dataset.values():
        backends = [source.backend for source in dataset_sources]
        if len(backends) < 2 or len(backends) != len(set(backends)):
            raise ReportError(
                "Each dataset must contain one formal run from at least two backends"
            )
        reference = dataset_sources[0]
        reference_cells = [
            (record.get("task_id"), record.get("repetition"))
            for record in reference.records
            if record.get("phase") == "measurement"
            and record.get("terminal", True)
        ]
        reference_environment = reference.manifest.get("environment")
        reference_hardware = tuple(
            _manifest_value(reference_environment, key)
            for key in (
                "platform",
                "python",
                "python_implementation",
                "executable_bits",
                "processor",
                "gpu",
            )
        )
        for candidate in dataset_sources[1:]:
            cells = [
                (record.get("task_id"), record.get("repetition"))
                for record in candidate.records
                if record.get("phase") == "measurement"
                and record.get("terminal", True)
            ]
            if cells != reference_cells:
                raise ReportError(
                    "Dataset task order/grid differs for backend "
                    f"{candidate.backend}"
                )
            if candidate.dataset_versions != reference.dataset_versions:
                raise ReportError("Dataset version labels differ across backends")
            if candidate.git_commit != reference.git_commit:
                raise ReportError("Git commit differs across compared backends")
            if candidate.manifest.get("dataset") != reference.manifest.get(
                "dataset"
            ):
                raise ReportError("Dataset manifest differs across backends")
            if candidate.manifest.get("generation") != reference.manifest.get(
                "generation"
            ):
                raise ReportError("Generation configuration differs across backends")
            if candidate.manifest.get("protocol") != reference.manifest.get(
                "protocol"
            ):
                raise ReportError("Measurement protocol differs across backends")
            candidate_environment = candidate.manifest.get("environment")
            candidate_hardware = tuple(
                _manifest_value(candidate_environment, key)
                for key in (
                    "platform",
                    "python",
                    "python_implementation",
                    "executable_bits",
                    "processor",
                    "gpu",
                )
            )
            if candidate_hardware != reference_hardware:
                raise ReportError("Hardware environment differs across backends")

    return tuple(
        sorted(
            sources,
            key=lambda source: (
                source.dataset_label.casefold(),
                source.backend.casefold(),
                source.result_reference,
            ),
        )
    )


def _measurements(source: FormalSource) -> list[dict[str, Any]]:
    return [
        record
        for record in source.records
        if record.get("terminal", True)
        and record.get("phase") == "measurement"
    ]


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _usage_numbers(records: Iterable[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for record in records:
        usage = record.get("usage")
        value = usage.get(key) if isinstance(usage, dict) else None
        numeric = _number(value)
        if numeric is not None:
            values.append(numeric)
    return values


def _latencies(records: Iterable[dict[str, Any]]) -> list[float]:
    values: list[float] = []
    for record in records:
        value = record.get("cumulative_latency_ms")
        if value is None:
            value = record.get("latency_ms")
        numeric = _number(value)
        if numeric is not None:
            values.append(numeric)
    return values


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [record for record in records if record.get("status") == "success"]
    scores = [
        value
        for record in records
        if (value := _number(record.get("score"))) is not None
    ]
    latencies = _latencies(records)
    ttft = _usage_numbers(successful, "ttft_ms")
    throughput = _usage_numbers(successful, "output_tokens_per_second")
    memory = _usage_numbers(successful, "peak_gpu_memory_mb")
    responses: dict[str, set[str]] = {}
    for record in records:
        task_id = record.get("task_id")
        response = record.get("response_text")
        if isinstance(task_id, str) and isinstance(response, str):
            responses.setdefault(task_id, set()).add(response)
    return {
        "unique_tasks": len({str(record.get("task_id")) for record in records}),
        "attempts": len(records),
        "successful": len(successful),
        "failures": len(records) - len(successful),
        "success_rate": len(successful) / len(records) if records else 0.0,
        "scored": len(scores),
        "mean_score": sum(scores) / len(scores) if scores else None,
        "median_latency_ms": statistics.median(latencies) if latencies else None,
        "median_ttft_ms": statistics.median(ttft) if ttft else None,
        "median_throughput": (
            statistics.median(throughput) if throughput else None
        ),
        "peak_gpu_memory_mb": max(memory) if memory else None,
        "stable_tasks": sum(len(values) == 1 for values in responses.values()),
    }


def _display(value: object, digits: int = 3) -> str:
    numeric = _number(value)
    return "n/a" if numeric is None else f"{numeric:.{digits}f}"


def _csv_display(value: object) -> str:
    numeric = _number(value)
    return "" if numeric is None else f"{numeric:.6f}"


def _csv_bytes(header: list[str], rows: Iterable[list[object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _run_summary_csv(sources: tuple[FormalSource, ...]) -> bytes:
    header = [
        "dataset_versions",
        "dataset_sha256",
        "backend",
        "model_id",
        "model_revision",
        "git_commit",
        "unique_tasks",
        "warmup_attempts",
        "repetitions",
        "measurement_attempts",
        "successful_measurements",
        "failed_measurements",
        "success_rate",
        "scored_measurements",
        "mean_score",
        "median_latency_ms",
        "p95_latency_ms",
        "median_ttft_ms",
        "p95_ttft_ms",
        "median_output_tokens_per_second",
        "peak_gpu_memory_mib",
        "result_sha256",
        "manifest_sha256",
    ]
    rows: list[list[object]] = []
    for source in sources:
        summary = source.summary
        rows.append(
            [
                source.dataset_label,
                source.dataset_sha256,
                source.backend,
                source.model_id,
                source.model_revision,
                source.git_commit,
                summary["unique_tasks"],
                summary["warmup_attempts"],
                summary["repetitions"],
                summary["total_tasks"],
                summary["successful_tasks"],
                summary["total_tasks"] - summary["successful_tasks"],
                _csv_display(summary["success_rate"]),
                summary["scored_tasks"],
                _csv_display(summary["mean_score"]),
                _csv_display(summary["median_latency_ms"]),
                _csv_display(summary["p95_latency_ms"]),
                _csv_display(summary["median_ttft_ms"]),
                _csv_display(summary["p95_ttft_ms"]),
                _csv_display(summary["median_output_tokens_per_second"]),
                _csv_display(summary["peak_gpu_memory_mb"]),
                source.result_sha256,
                source.manifest_sha256,
            ]
        )
    return _csv_bytes(header, rows)


def _category_rows(
    sources: tuple[FormalSource, ...],
) -> list[tuple[FormalSource, str, dict[str, Any]]]:
    rows: list[tuple[FormalSource, str, dict[str, Any]]] = []
    for source in sources:
        by_category: dict[str, list[dict[str, Any]]] = {}
        for record in _measurements(source):
            category = record.get("category")
            label = category if isinstance(category, str) else "uncategorized"
            by_category.setdefault(label, []).append(record)
        for category in sorted(by_category, key=str.casefold):
            rows.append((source, category, _aggregate(by_category[category])))
    return rows


def _category_summary_csv(sources: tuple[FormalSource, ...]) -> bytes:
    header = [
        "dataset_versions",
        "backend",
        "category",
        "unique_tasks",
        "measurement_attempts",
        "successful_measurements",
        "failed_measurements",
        "success_rate",
        "scored_measurements",
        "mean_score",
        "median_latency_ms",
        "median_ttft_ms",
        "median_output_tokens_per_second",
        "peak_gpu_memory_mib",
        "stable_response_tasks",
    ]
    rows = []
    for source, category, aggregate in _category_rows(sources):
        rows.append(
            [
                source.dataset_label,
                source.backend,
                category,
                aggregate["unique_tasks"],
                aggregate["attempts"],
                aggregate["successful"],
                aggregate["failures"],
                _csv_display(aggregate["success_rate"]),
                aggregate["scored"],
                _csv_display(aggregate["mean_score"]),
                _csv_display(aggregate["median_latency_ms"]),
                _csv_display(aggregate["median_ttft_ms"]),
                _csv_display(aggregate["median_throughput"]),
                _csv_display(aggregate["peak_gpu_memory_mb"]),
                aggregate["stable_tasks"],
            ]
        )
    return _csv_bytes(header, rows)


def _failure_csv(sources: tuple[FormalSource, ...]) -> bytes:
    header = [
        "dataset_versions",
        "backend",
        "task_id",
        "category",
        "repetition",
        "status",
        "error",
    ]
    rows: list[list[object]] = []
    for source in sources:
        for record in _measurements(source):
            if record.get("status") == "success":
                continue
            rows.append(
                [
                    source.dataset_label,
                    source.backend,
                    record.get("task_id", ""),
                    record.get("category", ""),
                    record.get("repetition", ""),
                    record.get("status", "unknown"),
                    redact_local_paths(record.get("error", "")),
                ]
            )
    return _csv_bytes(header, rows)


def _markdown_report(sources: tuple[FormalSource, ...]) -> bytes:
    dataset_count = len({source.dataset_sha256 for source in sources})
    backend_count = len({source.backend for source in sources})
    task_count = sum(
        len(group[0].task_ids)
        for group in _group_sources(sources).values()
    )
    lines = [
        "# Rebuilt formal multimodal benchmark report",
        "",
        "This report was generated deterministically from preserved result JSONL "
        "and sidecar manifests. It did not rerun a model. Every source passed "
        "hash, dataset/media, clean-commit, model-identity, and formal-protocol "
        "validation before aggregation.",
        "",
        "## Scope",
        "",
        f"- {backend_count} model backends",
        f"- {dataset_count} versioned task sets",
        f"- {task_count} unique dataset tasks",
        "- exactly one successful warm-up followed by three complete measured "
        "repetitions per source",
        "- batch size 1, deterministic decoding, no retries, and no model reloads "
        "during measurement",
        "",
        "![Formal benchmark overview](overview.svg)",
        "",
        "## Run summary",
        "",
        "| Dataset | Backend | Tasks | Success | Mean score | Median TTFT | "
        "Median throughput | Peak GPU memory |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for source in sources:
        summary = source.summary
        lines.append(
            f"| {source.dataset_label} | `{source.backend}` | "
            f"{summary['unique_tasks']} | "
            f"{summary['successful_tasks']}/{summary['total_tasks']} | "
            f"{_display(summary['mean_score'])} | "
            f"{_display(summary['median_ttft_ms'], 1)} ms | "
            f"{_display(summary['median_output_tokens_per_second'], 1)} tok/s | "
            f"{_display(summary['peak_gpu_memory_mb'], 1)} MiB |"
        )

    lines.extend(
        [
            "",
            "Detailed, machine-readable values are in `run-summary.csv`. "
            "Throughput uses each model's native tokenizer and is most reliable "
            "for repeated comparisons of the same pinned model.",
            "",
            "## Category summary",
            "",
            "| Dataset | Backend | Category | Tasks | Success | Mean score | "
            "Median TTFT | Peak GPU memory |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for source, category, aggregate in _category_rows(sources):
        lines.append(
            f"| {source.dataset_label} | `{source.backend}` | `{category}` | "
            f"{aggregate['unique_tasks']} | "
            f"{aggregate['successful']}/{aggregate['attempts']} | "
            f"{_display(aggregate['mean_score'])} | "
            f"{_display(aggregate['median_ttft_ms'], 1)} ms | "
            f"{_display(aggregate['peak_gpu_memory_mb'], 1)} MiB |"
        )

    failed = sum(
        source.summary["total_tasks"] - source.summary["successful_tasks"]
        for source in sources
    )
    lines.extend(["", "## Failures", ""])
    if failed:
        lines.append(
            f"The sources contain {failed} failed measured attempts. Complete "
            "status and redacted error data are preserved in `failures.csv`."
        )
    else:
        lines.append(
            "No failed measured attempts were recorded. `failures.csv` is still "
            "emitted with its stable schema so downstream automation does not "
            "need a special case."
        )

    lines.extend(
        [
            "",
            "## Preserved evidence",
            "",
            "| Dataset | Backend | Result | Result SHA-256 | Manifest | Manifest SHA-256 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for source in sources:
        lines.append(
            f"| {source.dataset_label} | `{source.backend}` | "
            f"`{source.result_reference}` | `{source.result_sha256}` | "
            f"`{source.manifest_reference}` | `{source.manifest_sha256}` |"
        )

    command = [
        "python scripts/build_benchmark_report.py `",
        *[
            f"  --input {source.result_reference} `"
            for source in sources
        ],
        "  --output-dir <output-directory>",
    ]
    lines.extend(
        [
            "",
            "## Rebuild",
            "",
            "From the repository root:",
            "",
            "```powershell",
            *command,
            "```",
            "",
            "Then verify every source, output hash, generator hash, and the "
            "self-hashed build manifest:",
            "",
            "```powershell",
            "python scripts/build_benchmark_report.py `",
            "  --verify `",
            "  --output-dir <output-directory>",
            "```",
            "",
            "## Interpretation limits",
            "",
            "These results apply only to the pinned models, task files, media "
            "hashes, software environments, and hardware recorded by the source "
            "manifests. They are not a universal model ranking and do not "
            "represent user preference or production quality.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _group_sources(
    sources: tuple[FormalSource, ...],
) -> dict[str, list[FormalSource]]:
    grouped: dict[str, list[FormalSource]] = {}
    for source in sources:
        grouped.setdefault(source.dataset_sha256, []).append(source)
    return grouped


def _overview_svg(sources: tuple[FormalSource, ...]) -> bytes:
    grouped = _group_sources(sources)
    height = 164 + len(grouped) * 54 + len(sources) * 66 + 54
    palette = ("#58b8ff", "#ffb45e", "#72d6a0", "#c59cff", "#ff7f91")
    backend_colors = {
        backend: palette[index % len(palette)]
        for index, backend in enumerate(
            sorted({source.backend for source in sources}, key=str.casefold)
        )
    }
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" '
        f'height="{height}" viewBox="0 0 1200 {height}" role="img" '
        'aria-labelledby="title description">',
        '  <title id="title">Formal multimodal benchmark overview</title>',
        '  <desc id="description">Quality, time to first token, throughput, '
        'peak allocated GPU memory, and success for verified formal runs.</desc>',
        "  <defs>",
        '    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">',
        '      <stop offset="0" stop-color="#07111f"/>',
        '      <stop offset="1" stop-color="#0c1d32"/>',
        "    </linearGradient>",
        "    <style>",
        '      text { font-family: Inter, "Segoe UI", Arial, sans-serif; }',
        "      .eyebrow { font-size: 14px; font-weight: 700; letter-spacing: 2px; fill: #7f96ad; }",
        "      .title { font-size: 38px; font-weight: 700; fill: #f4f8fc; }",
        "      .dataset { font-size: 18px; font-weight: 700; fill: #dce8f3; }",
        "      .backend { font-size: 16px; font-weight: 700; fill: #f4f8fc; }",
        "      .metric { font-size: 14px; font-weight: 400; fill: #a9bbcd; }",
        "      .value { font-size: 18px; font-weight: 700; fill: #f4f8fc; }",
        "      .footnote { font-size: 13px; font-weight: 600; fill: #7f96ad; }",
        "    </style>",
        "  </defs>",
        f'  <rect width="1200" height="{height}" fill="url(#background)"/>',
        '  <text x="56" y="48" class="eyebrow">FORMAL LOCAL BENCHMARK</text>',
        '  <text x="56" y="100" class="title">Reproducible multimodal evidence</text>',
        '  <text x="56" y="132" class="metric">One warm-up + three measured repeats · batch 1 · deterministic decoding</text>',
        '  <line x1="56" y1="154" x2="1144" y2="154" stroke="#27415c"/>',
    ]
    y = 194
    for dataset_sources in grouped.values():
        label = html.escape(dataset_sources[0].dataset_label)
        tasks = len(dataset_sources[0].task_ids)
        lines.append(
            f'  <text x="56" y="{y}" class="dataset">{label} · {tasks} tasks</text>'
        )
        y += 34
        for source in dataset_sources:
            summary = source.summary
            color = backend_colors[source.backend]
            backend = html.escape(source.backend)
            lines.extend(
                [
                    f'  <rect x="56" y="{y - 20}" width="1088" height="54" rx="12" fill="#10243a"/>',
                    f'  <circle cx="78" cy="{y + 7}" r="6" fill="{color}"/>',
                    f'  <text x="94" y="{y + 13}" class="backend">{backend}</text>',
                    f'  <text x="310" y="{y}" class="metric">MEAN SCORE</text>',
                    f'  <text x="310" y="{y + 22}" class="value">{_display(summary["mean_score"])}</text>',
                    f'  <text x="490" y="{y}" class="metric">MEDIAN TTFT</text>',
                    f'  <text x="490" y="{y + 22}" class="value">{_display(summary["median_ttft_ms"], 1)} ms</text>',
                    f'  <text x="680" y="{y}" class="metric">THROUGHPUT</text>',
                    f'  <text x="680" y="{y + 22}" class="value">{_display(summary["median_output_tokens_per_second"], 1)} tok/s</text>',
                    f'  <text x="870" y="{y}" class="metric">PEAK MEMORY</text>',
                    f'  <text x="870" y="{y + 22}" class="value">{_display(summary["peak_gpu_memory_mb"], 1)} MiB</text>',
                    f'  <text x="1060" y="{y}" class="metric">SUCCESS</text>',
                    f'  <text x="1060" y="{y + 22}" class="value">{summary["successful_tasks"]}/{summary["total_tasks"]}</text>',
                ]
            )
            y += 66
        y += 20
    lines.extend(
        [
            f'  <line x1="56" y1="{height - 48}" x2="1144" y2="{height - 48}" stroke="#27415c"/>',
            f'  <text x="56" y="{height - 20}" class="footnote">PINNED MODELS AND DATA · HASH-VERIFIED SOURCES · NOT A UNIVERSAL RANKING</text>',
            "</svg>",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _generator_inventory(project_root: Path) -> list[dict[str, object]]:
    references = (
        "scripts/build_benchmark_report.py",
        "src/openmultimodal_lab/report_bundle.py",
        "src/openmultimodal_lab/reporting.py",
    )
    inventory: list[dict[str, object]] = []
    for reference in references:
        path = _project_artifact(project_root, reference)
        if not path.is_file():
            raise ReportError(f"Report generator source is missing: {reference}")
        inventory.append(
            {
                "path": reference,
                "sha256": _sha256_path(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return inventory


def build_report_bundle(
    sources: tuple[FormalSource, ...],
    *,
    project_root: str | Path,
) -> dict[str, bytes]:
    """Return every deterministic report-bundle file as UTF-8 bytes."""

    if not sources:
        raise ReportError("Cannot build a report bundle without formal sources")
    sources = tuple(
        sorted(
            sources,
            key=lambda source: (
                source.dataset_label.casefold(),
                source.backend.casefold(),
                source.result_reference,
            ),
        )
    )
    root = Path(project_root).resolve()
    outputs = {
        "report.md": _markdown_report(sources),
        "run-summary.csv": _run_summary_csv(sources),
        "category-summary.csv": _category_summary_csv(sources),
        "failures.csv": _failure_csv(sources),
        "overview.svg": _overview_svg(sources),
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "verified-formal-sources",
        "protocol": {
            "warmup_attempts": 1,
            "repetitions": 3,
            "batch_size": 1,
            "do_sample": False,
            "max_retries": 0,
            "measurement_model_reloads": 0,
        },
        "generators": _generator_inventory(root),
        "sources": [
            {
                "dataset_versions": list(source.dataset_versions),
                "dataset_sha256": source.dataset_sha256,
                "backend": source.backend,
                "model_id": source.model_id,
                "model_revision": source.model_revision,
                "git_commit": source.git_commit,
                "result": {
                    "path": source.result_reference,
                    "sha256": source.result_sha256,
                    "size_bytes": source.result_path.stat().st_size,
                },
                "manifest": {
                    "path": source.manifest_reference,
                    "sha256": source.manifest_sha256,
                    "size_bytes": source.manifest_path.stat().st_size,
                },
            }
            for source in sources
        ],
        "outputs": [
            {
                "path": name,
                "sha256": _sha256_bytes(content),
                "size_bytes": len(content),
            }
            for name, content in sorted(outputs.items())
        ],
    }
    manifest["manifest_sha256"] = _sha256_bytes(
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    outputs["build-manifest.json"] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return outputs


def write_report_bundle(output_dir: str | Path, files: dict[str, bytes]) -> None:
    """Write a complete bundle with per-file atomic replacements."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if set(files) != set(BUNDLE_FILENAMES):
        raise ReportError("Report bundle has an unexpected file set")
    for name in BUNDLE_FILENAMES:
        destination = output / name
        temporary = output / f".{name}.tmp"
        temporary.write_bytes(files[name])
        temporary.replace(destination)


def verify_report_bundle(
    output_dir: str | Path,
    *,
    project_root: str | Path,
) -> dict[str, Any]:
    """Verify the self-hash plus every source, generator, and output hash."""

    output = Path(output_dir)
    manifest_path = output / "build-manifest.json"
    manifest, _ = _read_manifest(manifest_path)
    if manifest.get("schema_version") != "1.0":
        raise ReportError("Build manifest schema_version must be 1.0")
    if manifest.get("status") != "verified-formal-sources":
        raise ReportError("Build manifest status is invalid")
    recorded_hash = manifest.get("manifest_sha256")
    hash_input = dict(manifest)
    hash_input.pop("manifest_sha256", None)
    calculated_hash = _sha256_bytes(
        json.dumps(
            hash_input,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    if recorded_hash != calculated_hash:
        raise ReportError("Build manifest self-hash does not match")

    root = Path(project_root).resolve()
    for section in ("generators", "sources", "outputs"):
        if not isinstance(manifest.get(section), list):
            raise ReportError(f"Build manifest {section} inventory is invalid")
    expected_generator_paths = {
        "scripts/build_benchmark_report.py",
        "src/openmultimodal_lab/report_bundle.py",
        "src/openmultimodal_lab/reporting.py",
    }
    actual_generator_paths = {
        generator.get("path")
        for generator in manifest["generators"]
        if isinstance(generator, dict)
    }
    if actual_generator_paths != expected_generator_paths:
        raise ReportError("Build manifest generator inventory is incomplete")
    output_names = [
        artifact.get("path")
        for artifact in manifest["outputs"]
        if isinstance(artifact, dict)
    ]
    if (
        len(output_names) != len(set(output_names))
        or set(output_names) != set(BUNDLE_FILENAMES[:-1])
    ):
        raise ReportError("Build manifest output inventory is incomplete")
    artifacts: list[tuple[Path, dict[str, Any]]] = []
    for generator in manifest["generators"]:
        if not isinstance(generator, dict):
            raise ReportError("Build manifest generator record is invalid")
        artifacts.append((_project_artifact(root, generator.get("path")), generator))
    source_paths: list[Path] = []
    for source in manifest["sources"]:
        if not isinstance(source, dict):
            raise ReportError("Build manifest source record is invalid")
        for key in ("result", "manifest"):
            artifact = source.get(key)
            if not isinstance(artifact, dict):
                raise ReportError(f"Build manifest source {key} is invalid")
            artifact_path = _project_artifact(root, artifact.get("path"))
            artifacts.append((artifact_path, artifact))
            if key == "result":
                source_paths.append(artifact_path)
    for artifact in manifest["outputs"]:
        if not isinstance(artifact, dict):
            raise ReportError("Build manifest output record is invalid")
        name = artifact.get("path")
        if not isinstance(name, str) or name not in BUNDLE_FILENAMES[:-1]:
            raise ReportError("Build manifest output path is invalid")
        artifacts.append((output / name, artifact))

    for path, artifact in artifacts:
        if not path.is_file():
            raise ReportError(f"Referenced report artifact is missing: {path.name}")
        if path.stat().st_size != artifact.get("size_bytes"):
            raise ReportError(f"Report artifact size mismatch: {path.name}")
        if _sha256_path(path) != artifact.get("sha256"):
            raise ReportError(f"Report artifact hash mismatch: {path.name}")

    rebuilt_sources = load_comparable_sources(
        source_paths,
        project_root=root,
    )
    rebuilt = build_report_bundle(rebuilt_sources, project_root=root)
    for name in BUNDLE_FILENAMES:
        path = output / name
        if not path.is_file() or path.read_bytes() != rebuilt[name]:
            raise ReportError(
                f"Report bundle is not byte-reproducible from sources: {name}"
            )
    return manifest

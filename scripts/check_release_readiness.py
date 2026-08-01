"""Audit evidence for public v1.0 without inferring owner decisions."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


VIDEO_SUFFIXES = frozenset(
    {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}
)
CANONICAL_DATASETS = (
    "examples/tasks/synthetic-v1.1.jsonl",
    "examples/tasks/synthetic-docs-v1.jsonl",
)
REVIEW_REPORTS_BY_DATASET = {
    "synthetic-v1.1": "docs/reports/2026-07-29-synthetic-v1.md",
    "synthetic-docs-v1": "docs/reports/2026-08-01-synthetic-docs-v1.md",
}
FORMAL_RESULTS = (
    (
        "docs/reports/results/2026-07-31-qwen3-vl-comparison-formal.jsonl",
        "qwen3-vl",
        "image",
    ),
    (
        "docs/reports/results/2026-07-31-smolvlm2-500m-comparison-formal.jsonl",
        "smolvlm2",
        "image",
    ),
    (
        "docs/reports/results/2026-08-02-qwen3-vl-docs-formal.jsonl",
        "qwen3-vl",
        "document",
    ),
    (
        "docs/reports/results/2026-08-02-smolvlm2-500m-docs-formal.jsonl",
        "smolvlm2",
        "document",
    ),
)
REQUIRED_DOCUMENTS = (
    "README.md",
    "README.zh-CN.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/01-goals-and-success.md",
    "docs/03-architecture.md",
    "docs/06-quality-and-open-source.md",
    "docs/evaluation-protocol.md",
    "docs/video-corpus-tooling.md",
    "docs/tutorials/first-reproducible-benchmark.md",
    "docs/reports/2026-08-02-security-review.md",
)
PERFORMANCE_FIELDS = (
    "preprocessing_ms",
    "ttft_ms",
    "generation_ms",
    "output_tokens_per_second",
    "peak_gpu_memory_mb",
)


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """One evidence-backed public-release requirement."""

    id: str
    passed: bool
    evidence: str


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name}:{line_number}: expected object")
        rows.append(value)
    return rows


def _formal_result_status(records: list[dict[str, Any]]) -> tuple[bool, str]:
    terminal = [record for record in records if record.get("terminal", True)]
    warmups = [record for record in terminal if record.get("phase") == "warmup"]
    measurements = [
        record for record in terminal if record.get("phase") != "warmup"
    ]
    repetition_values = [
        record.get("repetition", 1) for record in measurements
    ]
    valid_repetitions = all(
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
        for value in repetition_values
    )
    repetitions = set(repetition_values) if valid_repetitions else set()
    successful = [
        record for record in measurements if record.get("status") == "success"
    ]
    failures = [
        record for record in measurements if record.get("status") != "success"
    ]
    retries = len(records) - len(terminal)
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
        and record["status"].strip()
        and isinstance(record.get("error"), str)
        and record["error"].strip()
        for record in failures
    )
    tasks_by_repetition: dict[object, list[object]] = {}
    for record in measurements:
        tasks_by_repetition.setdefault(
            record.get("repetition", 1),
            [],
        ).append(record.get("task_id"))
    valid_task_ids = all(
        isinstance(task_id, str) and task_id.strip()
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
    measurement_reloads = sum(
        isinstance(record.get("usage"), dict)
        and isinstance(record["usage"].get("model_load_ms"), (int, float))
        and record["usage"]["model_load_ms"] > 0
        for record in measurements
    )
    passed = (
        len(warmups) == 1
        and warmups[0].get("status") == "success"
        and repetitions == {1, 2, 3}
        and bool(successful)
        and complete_metrics
        and complete_failures
        and complete_repeat_grid
        and retries == 0
        and measurement_reloads == 0
    )
    return passed, (
        f"warmups={len(warmups)}, measurements={len(measurements)}, "
        f"repetitions={len(repetitions)}, successful={len(successful)}, "
        f"failures={len(failures)}, complete_grid={complete_repeat_grid}, "
        f"retries={retries}, measurement_reloads={measurement_reloads}"
    )


def audit_release_readiness(root: Path) -> list[ReadinessCheck]:
    """Return the current requirement/evidence matrix."""

    root = root.resolve()
    checks: list[ReadinessCheck] = []
    tasks: list[dict[str, Any]] = []
    dataset_versions: set[str] = set()
    task_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    metadata_issues: list[str] = []
    video_tasks = 0

    for relative in CANONICAL_DATASETS:
        path = root / relative
        if not path.is_file():
            metadata_issues.append(f"missing {relative}")
            continue
        for task in _load_jsonl(path):
            tasks.append(task)
            task_id = str(task.get("id", ""))
            if task_id in task_ids:
                duplicate_ids.add(task_id)
            task_ids.add(task_id)
            metadata = task.get("metadata")
            if not isinstance(metadata, dict):
                metadata_issues.append(f"{task_id}: missing metadata")
                continue
            dataset_versions.add(str(metadata.get("dataset_version", "")))
            for key in (
                "dataset_version",
                "category",
                "language",
                "answer_format",
                "source",
                "generator",
                "license",
            ):
                if not isinstance(metadata.get(key), str) or not metadata[key].strip():
                    metadata_issues.append(f"{task_id}: invalid metadata.{key}")
            if metadata.get("source") != "project-generated":
                metadata_issues.append(f"{task_id}: source is not project-generated")
            if metadata.get("license") != "Apache-2.0":
                metadata_issues.append(f"{task_id}: license is not Apache-2.0")
            media = task.get("media", [])
            if any(
                Path(str(item)).suffix.casefold() in VIDEO_SUFFIXES
                for item in media
            ):
                video_tasks += 1

    checks.append(
        ReadinessCheck(
            "TASK-COUNT",
            len(task_ids) >= 100 and not duplicate_ids,
            f"{len(task_ids)} unique canonical tasks; target >=100; "
            f"duplicates={sorted(duplicate_ids)}",
        )
    )
    checks.append(
        ReadinessCheck(
            "TASK-PROVENANCE",
            bool(tasks) and not metadata_issues,
            "all canonical tasks have project-generated Apache-2.0 provenance"
            if not metadata_issues
            else "; ".join(metadata_issues[:5]),
        )
    )
    missing_review_reports = [
        version
        for version in sorted(dataset_versions)
        if version not in REVIEW_REPORTS_BY_DATASET
        or not (root / REVIEW_REPORTS_BY_DATASET[version]).is_file()
    ]
    checks.append(
        ReadinessCheck(
            "HUMAN-REVIEW",
            len(task_ids) >= 100 and not missing_review_reports,
            (
                f"review reports cover {sorted(dataset_versions)} and "
                f"the corpus has {len(task_ids)} tasks"
                if len(task_ids) >= 100 and not missing_review_reports
                else f"current tasks={len(task_ids)}; datasets missing a "
                f"review report={missing_review_reports}; final >=100-task "
                "review is required"
            ),
        )
    )
    checks.append(
        ReadinessCheck(
            "VIDEO-TASKS",
            video_tasks > 0,
            f"{video_tasks} canonical tasks reference short-video media",
        )
    )

    formal_by_modality: dict[str, set[str]] = {}
    formal_details: list[str] = []
    all_formal = True
    for relative, expected_backend, modality in FORMAL_RESULTS:
        path = root / relative
        if not path.is_file():
            all_formal = False
            formal_details.append(f"missing {relative}")
            continue
        records = _load_jsonl(path)
        passed, detail = _formal_result_status(records)
        actual_backends = {str(record.get("backend")) for record in records}
        passed = passed and actual_backends == {expected_backend}
        all_formal = all_formal and passed
        if passed:
            formal_by_modality.setdefault(modality, set()).add(expected_backend)
        formal_details.append(f"{path.name}: {detail}")

    real_backends = (
        set().union(*formal_by_modality.values())
        if formal_by_modality
        else set()
    )
    checks.append(
        ReadinessCheck(
            "TWO-REAL-MODELS",
            len(real_backends) >= 2,
            f"formal evidence backends={sorted(real_backends)}",
        )
    )
    for modality in ("image", "document", "video"):
        backends = formal_by_modality.get(modality, set())
        checks.append(
            ReadinessCheck(
                f"FORMAL-{modality.upper()}",
                len(backends) >= 2,
                f"formal {modality} evidence backends={sorted(backends)}",
            )
        )
    checks.append(
        ReadinessCheck(
            "FORMAL-PROTOCOL",
            all_formal,
            " | ".join(formal_details),
        )
    )

    missing_documents = [
        relative for relative in REQUIRED_DOCUMENTS if not (root / relative).is_file()
    ]
    checks.append(
        ReadinessCheck(
            "DOCUMENTATION",
            not missing_documents,
            "required English/Chinese, tutorial, protocol, security, and "
            "license documents exist"
            if not missing_documents
            else f"missing={missing_documents}",
        )
    )
    video_tutorial = root / "docs/tutorials/video-benchmark.md"
    checks.append(
        ReadinessCheck(
            "VIDEO-DEMO",
            video_tutorial.is_file(),
            "copyable canonical short-video tutorial/demo exists"
            if video_tutorial.is_file()
            else "canonical short-video tutorial/demo is not yet present",
        )
    )
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    ci_markers = ('"3.11"', '"3.12"', "Build wheel", "Smoke-test installed wheel")
    checks.append(
        ReadinessCheck(
            "LINUX-CI-CONTRACT",
            all(marker in workflow for marker in ci_markers),
            "CI declares Python 3.11/3.12, wheel build, and outside-checkout smoke",
        )
    )

    final_license_audit = (
        root / "docs/reports/final-dependency-license-audit.md"
    )
    checks.append(
        ReadinessCheck(
            "FINAL-LICENSE-AUDIT",
            final_license_audit.is_file(),
            "final dependency, model, media, PyAV, and FFmpeg audit exists"
            if final_license_audit.is_file()
            else "final dependency/PyAV-FFmpeg license audit is still required",
        )
    )
    final_windows = root / "docs/reports/final-fresh-windows-validation.md"
    checks.append(
        ReadinessCheck(
            "FINAL-FRESH-WINDOWS",
            final_windows.is_file(),
            "final clean Windows installation and execution evidence exists"
            if final_windows.is_file()
            else "final candidate must be rebuilt in a fresh Windows environment",
        )
    )
    final_linux_ci = root / "docs/reports/final-linux-ci-validation.md"
    checks.append(
        ReadinessCheck(
            "FINAL-LINUX-CI",
            final_linux_ci.is_file(),
            "final candidate GitHub Linux CI evidence exists"
            if final_linux_ci.is_file()
            else "final candidate GitHub Linux CI evidence is still required",
        )
    )

    approvals_path = root / "docs/release-approvals.json"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    approved_names = all(
        isinstance(approvals.get(key), str) and approvals[key].strip()
        for key in ("project_name", "package_name", "cli_name", "public_version")
    ) and dataset_versions.issubset(set(approvals.get("dataset_names", [])))
    checks.append(
        ReadinessCheck(
            "OWNER-NAMING-APPROVAL",
            approved_names,
            "project/package/CLI/dataset/public-version approvals are recorded"
            if approved_names
            else "one or more required naming approvals are intentionally unrecorded",
        )
    )
    checks.append(
        ReadinessCheck(
            "OWNER-PUBLICATION-APPROVAL",
            approvals.get("target_repository_visibility") == "public"
            and approvals.get("make_repository_public") is True
            and approvals.get("formal_release_authorized") is True,
            f"current={approvals.get('current_repository_visibility')}; "
            f"target={approvals.get('target_repository_visibility')}; "
            f"make_public={approvals.get('make_repository_public')}; "
            f"release={approvals.get('formal_release_authorized')}",
        )
    )
    final_validation = root / "docs/reports/final-candidate-validation.md"
    checks.append(
        ReadinessCheck(
            "FINAL-CANDIDATE-VALIDATION",
            final_validation.is_file(),
            "final Windows/Python/Linux/package validation report exists"
            if final_validation.is_file()
            else "final candidate validation must be rerun after corpus completion",
        )
    )
    return checks


def _render_text(checks: Iterable[ReadinessCheck]) -> str:
    rows = list(checks)
    lines = ["OpenMultimodalLab public-release readiness"]
    for check in rows:
        status = "PASS" if check.passed else "OPEN"
        lines.append(f"[{status}] {check.id}: {check.evidence}")
    lines.append(
        f"Ready: {'yes' if all(check.passed for check in rows) else 'no'} "
        f"({sum(check.passed for check in rows)}/{len(rows)} checks passed)"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero until every release requirement passes.",
    )
    args = parser.parse_args(argv)
    checks = audit_release_readiness(args.root)
    ready = all(check.passed for check in checks)
    if args.as_json:
        print(
            json.dumps(
                {
                    "ready": ready,
                    "checks": [asdict(check) for check in checks],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(_render_text(checks))
    return 1 if args.strict and not ready else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit evidence for public v1.0 without inferring owner decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from openmultimodal_lab.report_bundle import verify_report_bundle
from openmultimodal_lab.reporting import ReportError

try:
    from scripts.validate_human_review import audit_human_review
except ModuleNotFoundError:  # Direct execution adds scripts/, not its parent.
    from validate_human_review import audit_human_review


VIDEO_SUFFIXES = frozenset(
    {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}
)
CANONICAL_DATASETS = (
    "examples/tasks/synthetic-v1.1.jsonl",
    "examples/tasks/synthetic-docs-v1.jsonl",
    "examples/tasks/synthetic-video-v1.jsonl",
    "examples/tasks/synthetic-robustness-v1.jsonl",
)
REVIEW_REPORTS_BY_DATASET = {
    "synthetic-v1.1": "docs/reports/2026-07-29-synthetic-v1.md",
    "synthetic-docs-v1": "docs/reports/2026-08-01-synthetic-docs-v1.md",
}
REVIEW_RECORDS_BY_DATASET = {
    "synthetic-video-v1": (
        "examples/tasks/synthetic-video-v1.jsonl",
        "docs/reviews/synthetic-video-v1.json",
    ),
    "synthetic-robustness-v1": (
        "examples/tasks/synthetic-robustness-v1.jsonl",
        "docs/reviews/synthetic-robustness-v1.json",
    ),
}
FINAL_DATASET_VERSIONS = frozenset(
    {
        "synthetic-v1.1",
        "synthetic-docs-v1",
        "synthetic-video-v1",
        "synthetic-robustness-v1",
    }
)
FORMAL_RESULTS = (
    (
        "docs/reports/results/2026-08-10-qwen3-vl-v1.0.0-formal.jsonl",
        "qwen3-vl",
        ("image", "document", "video"),
    ),
    (
        "docs/reports/results/2026-08-10-smolvlm2-v1.0.0-formal.jsonl",
        "smolvlm2",
        ("image", "document", "video"),
    ),
)
REQUIRED_DOCUMENTS = (
    "README.md",
    "README.zh-CN.md",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "NOTICE",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "TRADEMARKS.md",
    "docs/01-goals-and-success.md",
    "docs/03-architecture.md",
    "docs/06-quality-and-open-source.md",
    "docs/evaluation-protocol.md",
    "docs/license-audit.md",
    "docs/report-bundles.md",
    "docs/robustness-corpus-tooling.md",
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
MAX_LICENSE_SNAPSHOT_BYTES = 4 * 1024 * 1024
MAX_LICENSE_REPORT_BYTES = 1024 * 1024
MAX_CONSTRAINTS_BYTES = 1024 * 1024
MAX_VALIDATION_REPORT_BYTES = 1024 * 1024
PACKAGE_PIN = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?==\S+")
COMMIT_LINE = re.compile(r"Candidate commit: `[0-9a-f]{40}`")


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


def _license_snapshot_status(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "machine-readable runtime license snapshot is missing"
    with path.open("rb") as handle:
        raw = handle.read(MAX_LICENSE_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_LICENSE_SNAPSHOT_BYTES:
        return False, "runtime license snapshot exceeds 4 MiB"
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return False, "runtime license snapshot is not valid UTF-8 JSON"
    if not isinstance(value, dict):
        return False, "runtime license snapshot must be a JSON object"

    recorded_hash = value.get("snapshot_sha256")
    hash_input = dict(value)
    hash_input.pop("snapshot_sha256", None)
    calculated_hash = hashlib.sha256(
        json.dumps(
            hash_input,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    repository = value.get("repository")
    models = value.get("models")
    ffmpeg = value.get("ffmpeg")
    packages = value.get("packages")
    commit = repository.get("commit") if isinstance(repository, dict) else None
    immutable_commit = (
        isinstance(commit, str)
        and len(commit) == 40
        and all(character in "0123456789abcdef" for character in commit)
    )
    model_records_valid = (
        isinstance(models, list)
        and len(models) >= 2
        and all(
            isinstance(model, dict)
            and model.get("license") == "Apache-2.0"
            and isinstance(model.get("revision"), str)
            and len(model["revision"]) == 40
            and all(
                character in "0123456789abcdef"
                for character in model["revision"]
            )
            for model in models
        )
    )
    package_records_valid = (
        isinstance(packages, list)
        and bool(packages)
        and all(
            isinstance(package, dict)
            and isinstance(package.get("name"), str)
            and bool(package["name"])
            and isinstance(package.get("versions"), list)
            and len(package["versions"]) == 1
            and isinstance(package.get("declared_licenses"), list)
            and len(package["declared_licenses"]) == 1
            and isinstance(package.get("license_classifications"), list)
            and bool(package["license_classifications"])
            for package in packages
        )
    )
    bundled_binaries = (
        ffmpeg.get("bundled_binaries", [])
        if isinstance(ffmpeg, dict)
        else []
    )
    binary_records_valid = (
        isinstance(bundled_binaries, list)
        and bool(bundled_binaries)
        and all(
            isinstance(binary, dict)
            and isinstance(binary.get("name"), str)
            and bool(binary["name"])
            and isinstance(binary.get("size_bytes"), int)
            and not isinstance(binary["size_bytes"], bool)
            and binary["size_bytes"] > 0
            and isinstance(binary.get("sha256"), str)
            and len(binary["sha256"]) == 64
            and all(
                character in "0123456789abcdef"
                for character in binary["sha256"]
            )
            for binary in bundled_binaries
        )
    )
    ffmpeg_valid = (
        isinstance(ffmpeg, dict)
        and ffmpeg.get("bundled_runtime_allowed") is False
        and set(ffmpeg.get("gpl_markers_found", []))
        == {"libx264", "libx265"}
        and set(ffmpeg.get("version3_markers_found", []))
        == {"libopencore-amrnb", "libopencore-amrwb"}
        and ffmpeg.get("nonfree_markers_found") == []
        and ffmpeg.get("effective_ffmpeg_license")
        == "GPL-3.0-or-later"
        and binary_records_valid
    )
    passed = (
        value.get("schema_version") == "1.0"
        and value.get("status") == "PASS"
        and value.get("distribution_scope")
        == "source-only-no-runtime-binaries"
        and value.get("findings") == []
        and package_records_valid
        and isinstance(repository, dict)
        and repository.get("dirty") is False
        and repository.get("forbidden_runtime_files") == []
        and immutable_commit
        and model_records_valid
        and ffmpeg_valid
        and isinstance(recorded_hash, str)
        and recorded_hash == calculated_hash
    )
    return passed, (
        f"status={value.get('status')}, packages="
        f"{len(packages) if isinstance(packages, list) else 0}, "
        f"models={len(models) if isinstance(models, list) else 0}, "
        f"ffmpeg_binaries="
        f"{len(bundled_binaries)}, "
        f"clean="
        f"{repository.get('dirty') is False if isinstance(repository, dict) else False}, "
        f"hash_match={recorded_hash == calculated_hash}"
    )


def _constraints_status(
    path: Path,
    snapshot_path: Path,
) -> tuple[bool, str]:
    if not path.is_file():
        return False, "exact runtime constraints are missing"
    with path.open("rb") as handle:
        raw = handle.read(MAX_CONSTRAINTS_BYTES + 1)
    if len(raw) > MAX_CONSTRAINTS_BYTES:
        return False, "runtime constraints exceed 1 MiB"
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError:
        return False, "runtime constraints are not UTF-8"
    if not lines or any(not PACKAGE_PIN.fullmatch(line) for line in lines):
        return False, "runtime constraints are not exact name==version pins"
    if lines != sorted(lines) or len(lines) != len(set(lines)):
        return False, "runtime constraints are not sorted and unique"
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False, "runtime snapshot cannot be read for constraints"
    packages = snapshot.get("packages") if isinstance(snapshot, dict) else None
    if not isinstance(packages, list):
        return False, "runtime snapshot package inventory is invalid"
    expected = sorted(
        f"{package['name']}=={package['versions'][0]}"
        for package in packages
        if isinstance(package, dict)
        and package.get("name") != "openmultimodal-lab"
        and isinstance(package.get("versions"), list)
        and len(package["versions"]) == 1
    )
    return lines == expected, (
        f"pins={len(lines)}, match_snapshot={lines == expected}"
    )


def _license_report_status(
    path: Path,
    snapshot_path: Path,
) -> tuple[bool, str]:
    if not path.is_file():
        return False, "signed final license report is missing"
    with path.open("rb") as handle:
        raw = handle.read(MAX_LICENSE_REPORT_BYTES + 1)
    if len(raw) > MAX_LICENSE_REPORT_BYTES:
        return False, "final license report exceeds 1 MiB"
    try:
        text = raw.decode("utf-8")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False, "final license report or snapshot is unreadable"
    snapshot_hash = (
        snapshot.get("snapshot_sha256")
        if isinstance(snapshot, dict)
        else None
    )
    markers = (
        "# Final dependency and license audit",
        "Outcome: PASS",
        "Reviewer:",
        "Review date:",
        f"Snapshot SHA-256: `{snapshot_hash}`",
    )
    missing = [marker for marker in markers if marker not in text]
    return not missing, (
        "signed report markers complete"
        if not missing
        else f"signed report markers missing={missing}"
    )


def _video_demo_status(root: Path) -> tuple[bool, str]:
    tutorial = root / "docs/tutorials/video-benchmark.md"
    artifact = root / "docs/assets/video-benchmark-demo.gif"
    generator = root / "scripts/build_video_demo.py"
    missing = [
        path.relative_to(root).as_posix()
        for path in (tutorial, artifact, generator)
        if not path.is_file()
    ]
    if missing:
        return False, f"missing={missing}"
    data = artifact.read_bytes()
    if not data.startswith((b"GIF87a", b"GIF89a")):
        return False, "demo artifact is not a GIF"
    if not 10_000 < len(data) < 4 * 1024 * 1024:
        return False, f"demo GIF has unexpected size={len(data)}"
    tutorial_text = tutorial.read_text(encoding="utf-8")
    markers = (
        "video-benchmark-demo.gif",
        "video-right-end",
        "Qwen3-VL-2B answered `right` and passed",
        "SmolVLM2-500M",
        "answered `left.` and failed",
        "scripts/build_video_demo.py",
    )
    missing_markers = [
        marker for marker in markers if marker not in tutorial_text
    ]
    return not missing_markers, (
        f"GIF bytes={len(data)} and tutorial provenance markers are complete"
        if not missing_markers
        else f"tutorial markers missing={missing_markers}"
    )


def _validation_report_status(
    path: Path,
    *,
    heading: str,
    required_markers: tuple[str, ...],
) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"{path.name} is missing"
    with path.open("rb") as handle:
        raw = handle.read(MAX_VALIDATION_REPORT_BYTES + 1)
    if len(raw) > MAX_VALIDATION_REPORT_BYTES:
        return False, f"{path.name} exceeds 1 MiB"
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return False, f"{path.name} is not UTF-8"
    markers = (heading, "Outcome: PASS", "Validation date:", *required_markers)
    missing = [marker for marker in markers if marker not in text]
    if not COMMIT_LINE.search(text):
        missing.append("Candidate commit: `<40 lowercase hex>`")
    return not missing, (
        "validation evidence markers complete"
        if not missing
        else f"validation markers missing={missing}"
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
    review_issues: list[str] = []
    for version in sorted(dataset_versions):
        if version in REVIEW_RECORDS_BY_DATASET:
            dataset_relative, review_relative = REVIEW_RECORDS_BY_DATASET[
                version
            ]
            findings = audit_human_review(
                root / dataset_relative,
                root / review_relative,
            )
            if findings:
                review_issues.append(
                    f"{version}: {len(findings)} open review findings"
                )
        elif version not in REVIEW_REPORTS_BY_DATASET or not (
            root / REVIEW_REPORTS_BY_DATASET[version]
        ).is_file():
            review_issues.append(f"{version}: review evidence is missing")
    checks.append(
        ReadinessCheck(
            "HUMAN-REVIEW",
            len(task_ids) >= 100 and not review_issues,
            (
                f"review evidence covers {sorted(dataset_versions)} and "
                f"the corpus has {len(task_ids)} tasks"
                if len(task_ids) >= 100 and not review_issues
                else f"current tasks={len(task_ids)}; review issues="
                f"{review_issues}; final owner review is required"
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
    for relative, expected_backend, modalities in FORMAL_RESULTS:
        path = root / relative
        if not path.is_file():
            all_formal = False
            formal_details.append(f"missing {relative}")
            continue
        records = _load_jsonl(path)
        passed, detail = _formal_result_status(records)
        actual_backends = {str(record.get("backend")) for record in records}
        actual_versions = {
            str(record.get("dataset_version"))
            for record in records
            if record.get("phase") == "measurement"
        }
        passed = (
            passed
            and actual_backends == {expected_backend}
            and actual_versions == FINAL_DATASET_VERSIONS
        )
        all_formal = all_formal and passed
        if passed:
            for modality in modalities:
                formal_by_modality.setdefault(modality, set()).add(
                    expected_backend
                )
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
    baseline_bundle = root / "docs/reports/v1.0.0-candidate"
    try:
        bundle_manifest = verify_report_bundle(
            baseline_bundle,
            project_root=root,
        )
        bundle_passed = len(bundle_manifest.get("sources", [])) == 2
        bundle_evidence = (
            f"verified sources={len(bundle_manifest.get('sources', []))}, "
            f"outputs={len(bundle_manifest.get('outputs', []))}"
        )
    except (OSError, ReportError, ValueError) as exc:
        bundle_passed = False
        bundle_evidence = f"baseline bundle verification failed: {exc}"
    checks.append(
        ReadinessCheck(
            "REPORT-BUNDLE-TOOLING",
            bundle_passed,
            bundle_evidence,
        )
    )
    video_demo_passed, video_demo_evidence = _video_demo_status(root)
    checks.append(
        ReadinessCheck(
            "VIDEO-DEMO",
            video_demo_passed,
            video_demo_evidence,
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

    final_license_report = (
        root / "docs/reports/final-dependency-license-audit.md"
    )
    final_license_snapshot = (
        root / "docs/reports/results/final-runtime-license-audit.json"
    )
    final_constraints = (
        root / "requirements/model-windows-py311-constraints.txt"
    )
    license_snapshot_passed, license_snapshot_evidence = (
        _license_snapshot_status(final_license_snapshot)
    )
    constraints_passed, constraints_evidence = _constraints_status(
        final_constraints,
        final_license_snapshot,
    )
    report_passed, report_evidence = _license_report_status(
        final_license_report,
        final_license_snapshot,
    )
    final_license_passed = (
        report_passed and constraints_passed and license_snapshot_passed
    )
    checks.append(
        ReadinessCheck(
            "FINAL-LICENSE-AUDIT",
            final_license_passed,
            (
                "final report, exact constraints, and verified runtime "
                f"snapshot exist; {license_snapshot_evidence}; "
                f"{constraints_evidence}; {report_evidence}"
                if final_license_passed
                else "final report, exact constraints, and verified clean "
                f"runtime snapshot are required; {license_snapshot_evidence}; "
                f"{constraints_evidence}; {report_evidence}"
            ),
        )
    )
    final_windows = root / "docs/reports/final-fresh-windows-validation.md"
    windows_passed, windows_evidence = _validation_report_status(
        final_windows,
        heading="# Final fresh Windows validation",
        required_markers=(
            "Fresh environment:",
            "Wheel SHA-256:",
            "Outside-checkout smoke: PASS",
        ),
    )
    checks.append(
        ReadinessCheck(
            "FINAL-FRESH-WINDOWS",
            windows_passed,
            windows_evidence,
        )
    )
    final_linux_ci = root / "docs/reports/final-linux-ci-validation.md"
    linux_passed, linux_evidence = _validation_report_status(
        final_linux_ci,
        heading="# Final GitHub Linux CI validation",
        required_markers=(
            "GitHub Actions run: https://github.com/",
            "test (3.11): PASS",
            "test (3.12): PASS",
            "repository-quality: PASS",
        ),
    )
    checks.append(
        ReadinessCheck(
            "FINAL-LINUX-CI",
            linux_passed,
            linux_evidence,
        )
    )

    approvals_path = root / "docs/release-approvals.json"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    approved_name_fields = all(
        isinstance(approvals.get(key), str) and approvals[key].strip()
        for key in (
            "project_name",
            "package_name",
            "import_module",
            "cli_name",
            "video_dataset_name",
            "robustness_dataset_name",
            "public_version",
        )
    )
    approved_datasets = set(approvals.get("dataset_names", []))
    approved_names = (
        approved_name_fields
        and dataset_versions.issubset(approved_datasets)
        and approvals.get("video_dataset_name") in approved_datasets
        and approvals.get("robustness_dataset_name") in approved_datasets
    )
    checks.append(
        ReadinessCheck(
            "OWNER-NAMING-APPROVAL",
            approved_names,
            "project/package/import/CLI/dataset/public-version approvals are recorded"
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
    candidate_passed, candidate_evidence = _validation_report_status(
        final_validation,
        heading="# Final candidate validation",
        required_markers=(
            "Python 3.11: PASS",
            "Python 3.13: PASS",
            "Repository audit: PASS",
            "Wheel verification: PASS",
            "Report rebuild: PASS",
            "Security review: PASS",
        ),
    )
    checks.append(
        ReadinessCheck(
            "FINAL-CANDIDATE-VALIDATION",
            candidate_passed,
            candidate_evidence,
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
    technical = [
        check for check in rows if check.id != "OWNER-PUBLICATION-APPROVAL"
    ]
    lines.append(
        "Technically ready: "
        f"{'yes' if all(check.passed for check in technical) else 'no'} "
        f"({sum(check.passed for check in technical)}/{len(technical)} "
        "technical checks passed)"
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
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero until every release requirement passes.",
    )
    strict_group.add_argument(
        "--technical-strict",
        action="store_true",
        help=(
            "Return non-zero until every technical requirement passes; "
            "the separate owner publication decision is excluded."
        ),
    )
    args = parser.parse_args(argv)
    checks = audit_release_readiness(args.root)
    ready = all(check.passed for check in checks)
    technically_ready = all(
        check.passed
        for check in checks
        if check.id != "OWNER-PUBLICATION-APPROVAL"
    )
    if args.as_json:
        print(
            json.dumps(
                {
                    "ready": ready,
                    "technically_ready": technically_ready,
                    "checks": [asdict(check) for check in checks],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(_render_text(checks))
    if args.strict and not ready:
        return 1
    if args.technical_strict and not technically_ready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

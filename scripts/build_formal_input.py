"""Build or verify the SHA-bound input used by the formal model grid."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openmultimodal_lab.datasets import DatasetError, load_tasks  # noqa: E402


MAX_CONFIG_BYTES = 64 * 1024
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class FormalInputError(ValueError):
    """Raised when the frozen input contract cannot be satisfied."""


@dataclass(frozen=True, slots=True)
class FormalInputSummary:
    """Verified identity of one generated formal-evaluation input."""

    task_count: int
    sha256: str
    dataset_versions: tuple[str, ...]
    output_path: Path


def _read_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FormalInputError(f"Config does not exist or is not a file: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_CONFIG_BYTES:
        raise FormalInputError("Config exceeds the 64 KiB safety limit")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FormalInputError("Config is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise FormalInputError("Config must be a JSON object")
    return value


def _safe_source_path(project_root: Path, raw_path: object) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise FormalInputError("Every source path must be a non-empty string")
    posix = PurePosixPath(raw_path)
    if posix.is_absolute() or ".." in posix.parts or "\\" in raw_path:
        raise FormalInputError(f"Source path is not repository-relative: {raw_path}")
    resolved = (project_root / Path(*posix.parts)).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise FormalInputError(
            f"Source path leaves the repository: {raw_path}"
        ) from exc
    return resolved


def _required_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise FormalInputError(f"{label} must be a lowercase SHA-256 value")
    return value


def build_formal_input(
    config_path: Path,
    output_path: Path,
    *,
    project_root: Path = PROJECT_ROOT,
    verify_only: bool = False,
) -> FormalInputSummary:
    """Build or verify one byte-exact aggregate without renaming its datasets."""

    root = project_root.resolve()
    config = _read_config(config_path)
    if config.get("schema_version") != "1.0":
        raise FormalInputError("Unsupported formal-input schema_version")
    if config.get("purpose") != "formal-evaluation-input":
        raise FormalInputError("Config purpose must be 'formal-evaluation-input'")
    if config.get("public_version") != "v1.0.0":
        raise FormalInputError("Config public_version must be 'v1.0.0'")

    expected_count = config.get("expected_task_count")
    if not isinstance(expected_count, int) or isinstance(expected_count, bool):
        raise FormalInputError("expected_task_count must be an integer")
    if expected_count < 1:
        raise FormalInputError("expected_task_count must be positive")
    expected_output_hash = _required_sha256(
        config.get("expected_output_sha256"),
        "expected_output_sha256",
    )
    expected_versions = config.get("expected_dataset_versions")
    if not isinstance(expected_versions, list) or not all(
        isinstance(item, str) and item for item in expected_versions
    ):
        raise FormalInputError(
            "expected_dataset_versions must be a non-empty string list"
        )
    if not expected_versions or len(set(expected_versions)) != len(
        expected_versions
    ):
        raise FormalInputError("expected_dataset_versions must be unique")

    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise FormalInputError("sources must be a non-empty list")

    combined_parts: list[bytes] = []
    task_ids: set[str] = set()
    actual_versions: list[str] = []
    seen_paths: set[Path] = set()
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise FormalInputError(f"Source {index} must be an object")
        source_path = _safe_source_path(root, source.get("path"))
        if source_path in seen_paths:
            raise FormalInputError(f"Duplicate source path: {source.get('path')}")
        seen_paths.add(source_path)
        expected_source_hash = _required_sha256(
            source.get("sha256"),
            f"sources[{index}].sha256",
        )
        if not source_path.is_file():
            raise FormalInputError(f"Source does not exist: {source.get('path')}")
        raw = source_path.read_bytes()
        actual_source_hash = hashlib.sha256(raw).hexdigest()
        if actual_source_hash != expected_source_hash:
            raise FormalInputError(
                f"Source SHA-256 mismatch: {source.get('path')}"
            )
        if not raw.endswith(b"\n") or b"\r" in raw:
            raise FormalInputError(
                f"Source must use LF and end with a newline: {source.get('path')}"
            )
        try:
            tasks = load_tasks(source_path, media_root=root)
        except DatasetError as exc:
            raise FormalInputError(str(exc)) from exc
        source_version_values = [
            task.metadata.get("dataset_version") for task in tasks
        ]
        if not all(
            isinstance(item, str) and item for item in source_version_values
        ):
            raise FormalInputError(
                f"Source must contain one dataset version: {source.get('path')}"
            )
        source_versions = set(source_version_values)
        if len(source_versions) != 1:
            raise FormalInputError(
                f"Source must contain one dataset version: {source.get('path')}"
            )
        dataset_version = next(iter(source_versions))
        if dataset_version in actual_versions:
            raise FormalInputError(f"Duplicate dataset version: {dataset_version}")
        actual_versions.append(dataset_version)
        for task in tasks:
            if task.id in task_ids:
                raise FormalInputError(f"Duplicate task id across sources: {task.id}")
            if task.metadata.get("source") != "project-generated":
                raise FormalInputError(f"Task source is not project-generated: {task.id}")
            if task.metadata.get("license") != "Apache-2.0":
                raise FormalInputError(f"Task license is not Apache-2.0: {task.id}")
            task_ids.add(task.id)
        combined_parts.append(raw)

    combined = b"".join(combined_parts)
    actual_output_hash = hashlib.sha256(combined).hexdigest()
    if len(task_ids) != expected_count:
        raise FormalInputError(
            f"Task count mismatch: expected {expected_count}, got {len(task_ids)}"
        )
    if actual_versions != expected_versions:
        raise FormalInputError(
            "Dataset version order mismatch: " + ", ".join(actual_versions)
        )
    if actual_output_hash != expected_output_hash:
        raise FormalInputError("Aggregate output SHA-256 mismatch")

    resolved_output = output_path.resolve()
    if resolved_output == config_path.resolve() or resolved_output in seen_paths:
        raise FormalInputError("Output path overlaps a config or source file")
    if verify_only:
        if not resolved_output.is_file():
            raise FormalInputError(f"Output does not exist: {output_path}")
        if resolved_output.read_bytes() != combined:
            raise FormalInputError("Existing output does not match frozen input")
    else:
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_bytes(combined)

    return FormalInputSummary(
        task_count=len(task_ids),
        sha256=actual_output_hash,
        dataset_versions=tuple(actual_versions),
        output_path=resolved_output,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify an existing output instead of writing it.",
    )
    args = parser.parse_args(argv)
    try:
        summary = build_formal_input(
            args.config,
            args.output,
            verify_only=args.verify,
        )
    except FormalInputError as exc:
        print(f"Formal input error: {exc}", file=sys.stderr)
        return 2
    action = "Verified" if args.verify else "Built"
    print(
        f"{action} formal evaluation input: {summary.task_count} tasks, "
        f"sha256={summary.sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

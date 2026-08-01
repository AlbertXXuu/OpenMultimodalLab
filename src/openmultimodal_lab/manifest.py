"""Portable experiment manifests for reproducible benchmark runs."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import EvaluationTask, RunRecord


MANIFEST_SCHEMA_VERSION = "1.0"


class ManifestResumeError(ValueError):
    """Raised when a stored manifest is incompatible with a resumed run."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _git_state(
    root: Path,
    ignored_paths: Iterable[Path] = (),
) -> dict[str, Any]:
    def run(*arguments: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.stdout.strip()

    commit = run("rev-parse", "HEAD")
    status_arguments = [
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        ".",
    ]
    for ignored_path in ignored_paths:
        try:
            relative = ignored_path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        status_arguments.append(f":(exclude){relative.as_posix()}")
    status = run(*status_arguments)
    return {
        "commit": commit or "unavailable",
        "dirty": status is None or bool(status),
    }


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution in (
        "openmultimodal-lab",
        "torch",
        "torchvision",
        "transformers",
        "accelerate",
        "huggingface-hub",
        "num2words",
        "pillow",
        "safetensors",
        "tokenizers",
    ):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            continue
    return versions


def manifest_path_for(output_path: str | Path) -> Path:
    output = Path(output_path)
    return output.with_suffix(output.suffix + ".manifest.json")


def load_run_manifest(path: str | Path) -> dict[str, Any]:
    """Load one run manifest as a JSON object."""

    source = Path(path)
    if not source.is_file():
        raise ManifestResumeError(
            f"cannot resume because manifest does not exist: {source}"
        )
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestResumeError(
            f"cannot resume because manifest is unreadable: {source}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ManifestResumeError("run manifest must be a JSON object")
    return value


def validate_resume_manifest(
    existing: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    output_path: str | Path,
) -> None:
    """Reject a resume when inputs, code, environment, or protocol changed."""

    status = existing.get("status")
    if status not in {"started", "failed"}:
        raise ManifestResumeError(
            f"run status is '{status}'; only started or failed runs can resume"
        )

    for section in (
        "schema_version",
        "dataset",
        "backend",
        "generation",
        "protocol",
        "environment",
    ):
        if existing.get(section) != candidate.get(section):
            raise ManifestResumeError(
                f"resume configuration mismatch in '{section}'"
            )

    existing_output = existing.get("output")
    candidate_output = candidate.get("output")
    if not isinstance(existing_output, Mapping) or not isinstance(
        candidate_output,
        Mapping,
    ):
        raise ManifestResumeError("run manifest has an invalid output section")
    if existing_output.get("path") != candidate_output.get("path"):
        raise ManifestResumeError(
            "resume configuration mismatch in 'output.path'"
        )

    output = Path(output_path)
    if not output.is_file():
        raise ManifestResumeError(
            f"cannot resume because output does not exist: {output}"
        )
    declared_size = existing_output.get("size_bytes")
    if (
        not isinstance(declared_size, int)
        or isinstance(declared_size, bool)
        or declared_size < 0
    ):
        raise ManifestResumeError(
            "run manifest has an invalid 'output.size_bytes'"
        )
    if output.stat().st_size != declared_size:
        raise ManifestResumeError(
            "existing output size does not match the run manifest"
        )
    declared_sha256 = existing_output.get("sha256")
    if (
        not isinstance(declared_sha256, str)
        or len(declared_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in declared_sha256
        )
    ):
        raise ManifestResumeError(
            "run manifest has an invalid 'output.sha256'"
        )
    if _sha256(output) != declared_sha256:
        raise ManifestResumeError(
            "existing output SHA-256 does not match the run manifest"
        )


def validate_resume_record_count(
    existing: Mapping[str, Any],
    actual_count: int,
) -> None:
    """Check a manifest's durable count when a checkpoint declared one."""

    if (
        not isinstance(actual_count, int)
        or isinstance(actual_count, bool)
        or actual_count < 0
    ):
        raise ValueError("actual_count must be a non-negative integer")
    declared_count = existing.get("records_written")
    if (
        not isinstance(declared_count, int)
        or isinstance(declared_count, bool)
        or declared_count < 0
    ):
        raise ManifestResumeError(
            "run manifest has an invalid 'records_written'"
        )
    if declared_count != actual_count:
        raise ManifestResumeError(
            "existing output record count does not match the run manifest"
        )


def prepare_resumed_manifest(
    existing: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an in-progress manifest while preserving run provenance."""

    resumed = dict(existing)
    for key in (
        "completed_at_utc",
        "error",
    ):
        resumed.pop(key, None)
    previous_resume_count = existing.get("resume_count", 0)
    if (
        not isinstance(previous_resume_count, int)
        or isinstance(previous_resume_count, bool)
        or previous_resume_count < 0
    ):
        raise ManifestResumeError(
            "run manifest has an invalid 'resume_count'"
        )
    resumed.update(
        {
            "status": "started",
            "resumed_at_utc": datetime.now(timezone.utc).isoformat(),
            "resume_count": previous_resume_count + 1,
        }
    )
    return resumed


def checkpoint_run_manifest(
    manifest: Mapping[str, Any],
    records: Iterable[RunRecord | Mapping[str, Any]],
    *,
    output_path: str | Path,
) -> dict[str, Any]:
    """Record a durable in-progress prefix and its output identity."""

    checkpoint = dict(manifest)
    record_list = list(records)

    def phase(record: RunRecord | Mapping[str, Any]) -> str:
        if isinstance(record, Mapping):
            return str(record.get("phase", "measurement"))
        return record.phase

    def terminal(record: RunRecord | Mapping[str, Any]) -> bool:
        if isinstance(record, Mapping):
            return bool(record.get("terminal", True))
        return record.terminal

    terminal_records = [record for record in record_list if terminal(record)]

    output_file = Path(output_path)
    output = dict(checkpoint.get("output", {}))
    output.update(
        {
            "sha256": _sha256(output_file),
            "size_bytes": output_file.stat().st_size,
        }
    )
    checkpoint.update(
        {
            "status": "started",
            "checkpointed_at_utc": datetime.now(timezone.utc).isoformat(),
            "records_written": len(record_list),
            "generation_invocations": len(record_list),
            "retry_records": len(record_list) - len(terminal_records),
            "warmup_records": sum(
                phase(record) == "warmup" for record in terminal_records
            ),
            "measurement_records": sum(
                phase(record) != "warmup" for record in terminal_records
            ),
            "output": output,
        }
    )
    return checkpoint


def build_run_manifest(
    *,
    dataset_path: str | Path,
    output_path: str | Path,
    media_root: str | Path,
    tasks: Iterable[EvaluationTask],
    backend: str,
    model_id: str,
    model_revision: str,
    max_new_tokens: int,
    warmup: int,
    repetitions: int,
    max_retries: int = 0,
    timeout_seconds: float | None = None,
    categories: Iterable[str],
    gpu_summary: str,
    project_root: str | Path,
) -> dict[str, Any]:
    """Build a manifest without leaking user-specific absolute paths."""

    root = Path(project_root).resolve()
    dataset = Path(dataset_path)
    output = Path(output_path)
    output_manifest = manifest_path_for(output)
    media_base = Path(media_root)
    task_list = list(tasks)
    media_entries: list[dict[str, str]] = []
    seen_media: set[Path] = set()

    for task in task_list:
        for item in task.media:
            media = Path(item)
            resolved = media if media.is_absolute() else media_base / media
            resolved = resolved.resolve()
            if resolved in seen_media:
                continue
            seen_media.add(resolved)
            media_entries.append(
                {
                    "path": _portable_path(resolved, root),
                    "sha256": _sha256(resolved),
                }
            )

    selected_categories = list(dict.fromkeys(categories))
    dataset_versions = sorted(
        {
            str(task.metadata.get("dataset_version", "unspecified"))
            for task in task_list
        }
    )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "status": "started",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": _portable_path(dataset, root),
            "sha256": _sha256(dataset.resolve()),
            "versions": dataset_versions,
            "task_ids": [task.id for task in task_list],
            "media": media_entries,
        },
        "output": {"path": _portable_path(output, root)},
        "backend": {
            "name": backend,
            "model_id": model_id,
            "model_revision": model_revision,
        },
        "generation": {
            "do_sample": False,
            "max_new_tokens": max_new_tokens,
            "batch_size": 1,
        },
        "protocol": {
            "warmup_attempts": warmup,
            "repetitions": repetitions,
            "max_retries": max_retries,
            "attempt_timeout_seconds": timeout_seconds,
            "retryable_statuses": ["generation_error", "timeout"],
            "retry_backoff": "none",
            "timeout_boundary": (
                "adapter inference after one-time model loading; cooperative "
                "for built-in backends"
            ),
            "task_order": "dataset order repeated without shuffle",
            "categories": selected_categories,
            "gpu_synchronization": "adapter timing boundaries when CUDA is active",
            "ttft_boundary": "generation start to first-token logits completion",
            "throughput_boundary": "generated tokens over model.generate duration",
            "peak_memory_boundary": "maximum allocated CUDA memory during generation",
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "executable_bits": 64 if sys.maxsize > 2**32 else 32,
            "processor": platform.processor() or "unavailable",
            "gpu": gpu_summary,
            "packages": _package_versions(),
            "git": _git_state(
                root,
                (
                    output,
                    output_manifest,
                    output_manifest.with_suffix(
                        output_manifest.suffix + ".tmp"
                    ),
                ),
            ),
        },
    }


def finalize_run_manifest(
    manifest: Mapping[str, Any],
    records: Iterable[RunRecord | Mapping[str, Any]],
    *,
    status: str,
    error: str | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    finalized = dict(manifest)
    record_list = list(records)

    def phase(record: RunRecord | Mapping[str, Any]) -> str:
        if isinstance(record, Mapping):
            return str(record.get("phase", "measurement"))
        return record.phase

    def terminal(record: RunRecord | Mapping[str, Any]) -> bool:
        if isinstance(record, Mapping):
            return bool(record.get("terminal", True))
        return record.terminal

    terminal_records = [record for record in record_list if terminal(record)]

    finalized.update(
        {
            "status": status,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "records_written": len(record_list),
            "generation_invocations": len(record_list),
            "retry_records": len(record_list) - len(terminal_records),
            "warmup_records": sum(
                phase(record) == "warmup" for record in terminal_records
            ),
            "measurement_records": sum(
                phase(record) != "warmup" for record in terminal_records
            ),
            "error": error,
        }
    )
    if output_path is not None:
        output_file = Path(output_path)
        if output_file.is_file():
            output = dict(finalized.get("output", {}))
            output.update(
                {
                    "sha256": _sha256(output_file),
                    "size_bytes": output_file.stat().st_size,
                }
            )
            finalized["output"] = output
    return finalized


def write_run_manifest(path: str | Path, manifest: Mapping[str, Any]) -> None:
    """Sync a temporary JSON manifest and atomically replace the prior file."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    serialized = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(destination)
    if os.name != "nt":
        directory_descriptor = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

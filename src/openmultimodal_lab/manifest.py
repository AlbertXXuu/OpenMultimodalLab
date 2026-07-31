"""Portable experiment manifests for reproducible benchmark runs."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import EvaluationTask, RunRecord


MANIFEST_SCHEMA_VERSION = "1.0"


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


def _git_state(root: Path) -> dict[str, Any]:
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
    status = run("status", "--porcelain")
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
    categories: Iterable[str],
    gpu_summary: str,
    project_root: str | Path,
) -> dict[str, Any]:
    """Build a manifest without leaking user-specific absolute paths."""

    root = Path(project_root).resolve()
    dataset = Path(dataset_path)
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
        "output": {"path": _portable_path(Path(output_path), root)},
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
            "git": _git_state(root),
        },
    }


def finalize_run_manifest(
    manifest: Mapping[str, Any],
    records: Iterable[RunRecord | Mapping[str, Any]],
    *,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    finalized = dict(manifest)
    record_list = list(records)

    def phase(record: RunRecord | Mapping[str, Any]) -> str:
        if isinstance(record, Mapping):
            return str(record.get("phase", "measurement"))
        return record.phase

    finalized.update(
        {
            "status": status,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "records_written": len(record_list),
            "warmup_records": sum(
                phase(record) == "warmup" for record in record_list
            ),
            "measurement_records": sum(
                phase(record) != "warmup" for record in record_list
            ),
            "error": error,
        }
    )
    return finalized


def write_run_manifest(path: str | Path, manifest: Mapping[str, Any]) -> None:
    """Atomically replace a JSON manifest."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(destination)

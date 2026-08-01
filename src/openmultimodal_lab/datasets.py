"""JSONL task loading and validation."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .models import EvaluationTask
from .privacy import portable_media_references, portable_path_reference


MAX_DATASET_BYTES = 16 * 1024 * 1024
MAX_JSONL_LINE_BYTES = 1024 * 1024


class DatasetError(ValueError):
    """Raised when a dataset cannot be safely interpreted."""


def available_categories(tasks: Iterable[EvaluationTask]) -> list[str]:
    """Return sorted, non-empty category names declared by the tasks."""

    categories = {
        category.strip()
        for task in tasks
        if isinstance((category := task.metadata.get("category")), str)
        and category.strip()
    }
    return sorted(categories)


def filter_tasks_by_categories(
    tasks: Iterable[EvaluationTask],
    categories: Iterable[str],
) -> list[EvaluationTask]:
    """Keep tasks whose exact category matches one of the requested values."""

    requested = {category.strip() for category in categories if category.strip()}
    if not requested:
        return list(tasks)

    return [
        task
        for task in tasks
        if isinstance((category := task.metadata.get("category")), str)
        and category.strip() in requested
    ]


def load_tasks(
    dataset_path: str | Path,
    *,
    media_root: str | Path | None = None,
    require_media: bool = True,
) -> list[EvaluationTask]:
    """Load a UTF-8 JSONL dataset and validate task identifiers and media."""

    path = Path(dataset_path)
    path_label = portable_path_reference(str(path))
    if not path.is_file():
        raise DatasetError(
            f"Dataset does not exist or is not a file: {path_label}"
        )
    size_bytes = path.stat().st_size
    if size_bytes > MAX_DATASET_BYTES:
        raise DatasetError(
            f"Dataset exceeds the {MAX_DATASET_BYTES // (1024 * 1024)} MiB "
            f"safety limit: {path_label}"
        )
    with path.open("rb") as handle:
        raw = handle.read(MAX_DATASET_BYTES + 1)
    if len(raw) > MAX_DATASET_BYTES:
        raise DatasetError(
            f"Dataset exceeds the {MAX_DATASET_BYTES // (1024 * 1024)} MiB "
            f"safety limit: {path_label}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        line_number = raw[: exc.start].count(b"\n") + 1
        raise DatasetError(
            f"{path_label}:{line_number}: dataset is not valid UTF-8"
        ) from exc

    root = Path(media_root) if media_root is not None else Path.cwd()
    tasks: list[EvaluationTask] = []
    seen_ids: set[str] = set()

    for line_number, raw_line in enumerate(
        text.splitlines(keepends=True),
        start=1,
    ):
        if len(raw_line.encode("utf-8")) > MAX_JSONL_LINE_BYTES:
            raise DatasetError(
                f"{path_label}:{line_number}: JSONL line exceeds the "
                f"{MAX_JSONL_LINE_BYTES // 1024} KiB safety limit"
            )
        line = raw_line.strip()
        if not line:
            continue

        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(
                f"{path_label}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc

        if not isinstance(value, dict):
            raise DatasetError(
                f"{path_label}:{line_number}: each line must be a JSON object"
            )

        try:
            task = EvaluationTask.from_mapping(value)
        except ValueError as exc:
            raw_task_id = value.get("id")
            task_context = (
                f" task '{raw_task_id.strip()}'"
                if isinstance(raw_task_id, str) and raw_task_id.strip()
                else ""
            )
            raise DatasetError(
                f"{path_label}:{line_number}:{task_context} {exc}"
            ) from exc

        if task.id in seen_ids:
            raise DatasetError(
                f"{path_label}:{line_number}: duplicate task id '{task.id}'"
            )

        if require_media:
            for media_item in task.media:
                media_path = Path(media_item)
                resolved = (
                    media_path
                    if media_path.is_absolute()
                    else root / media_path
                )
                if not resolved.is_file():
                    media_label = portable_media_references(
                        (media_item,)
                    )[0]
                    raise DatasetError(
                        f"{path_label}:{line_number}: media for task "
                        f"'{task.id}' does not exist: {media_label}"
                    )

        seen_ids.add(task.id)
        tasks.append(task)

    if not tasks:
        raise DatasetError(f"Dataset contains no tasks: {path_label}")

    return tasks

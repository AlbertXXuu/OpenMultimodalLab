"""JSONL task loading and validation."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .models import EvaluationTask


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
    if not path.is_file():
        raise DatasetError(f"Dataset does not exist or is not a file: {path}")

    root = Path(media_root) if media_root is not None else Path.cwd()
    tasks: list[EvaluationTask] = []
    seen_ids: set[str] = set()

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError(
                    f"{path}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc

            if not isinstance(value, dict):
                raise DatasetError(f"{path}:{line_number}: each line must be a JSON object")

            try:
                task = EvaluationTask.from_mapping(value)
            except ValueError as exc:
                raise DatasetError(f"{path}:{line_number}: {exc}") from exc

            if task.id in seen_ids:
                raise DatasetError(f"{path}:{line_number}: duplicate task id '{task.id}'")

            if require_media:
                for media_item in task.media:
                    media_path = Path(media_item)
                    resolved = media_path if media_path.is_absolute() else root / media_path
                    if not resolved.is_file():
                        raise DatasetError(
                            f"{path}:{line_number}: media for task '{task.id}' "
                            f"does not exist: {resolved}"
                        )

            seen_ids.add(task.id)
            tasks.append(task)

    if not tasks:
        raise DatasetError(f"Dataset contains no tasks: {path}")

    return tasks

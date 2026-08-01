"""Generate deterministic visual-robustness assets and an optional task draft."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generate_synthetic_images import (
    BLUE,
    GREEN,
    ORANGE,
    PURPLE,
    RED,
    Canvas,
    Color,
)


WIDTH = 320
HEIGHT = 240
GENERATOR_REFERENCE = "scripts/generate_robustness_images.py"
REVIEW_PROFILE = "static-image-v1"
REVIEW_CHECKS = (
    "media_opens_and_renders",
    "robustness_condition_is_visible",
    "prompt_answer_matches_media",
    "answer_is_unambiguous",
    "license_and_provenance_confirmed",
)

LIGHT_RED: Color = (205, 128, 128)
LIGHT_BLUE: Color = (130, 160, 200)
LIGHT_GREEN: Color = (118, 166, 130)
NEUTRAL: Color = (148, 163, 184)
OCCLUDER: Color = (71, 85, 105)

Renderer = Callable[[], Canvas]


@dataclass(frozen=True, slots=True)
class SceneSpec:
    """One deterministic robustness scene and its reference attributes."""

    key: str
    factor: str
    color_name: str
    shape_name: str
    context_prompt: str
    context_category: str
    context_format: str
    context_answer: str | int
    renderer: Renderer


def _canvas(background: Color | None = None) -> Canvas:
    canvas = Canvas(WIDTH, HEIGHT)
    if background is not None:
        canvas.pixels[:] = bytes(background) * (WIDTH * HEIGHT)
    return canvas


def _draw_shape(
    canvas: Canvas,
    shape: str,
    center_x: int,
    center_y: int,
    color: Color,
    *,
    size: int,
) -> None:
    if shape == "square":
        canvas.rectangle(
            center_x - size,
            center_y - size,
            center_x + size,
            center_y + size,
            color,
        )
        return
    if shape == "circle":
        canvas.circle(center_x, center_y, size, color)
        return
    if shape == "triangle":
        canvas.triangle(
            (
                (center_x, center_y - size),
                (center_x - size, center_y + size),
                (center_x + size, center_y + size),
            ),
            color,
        )
        return
    raise ValueError(f"unsupported robustness shape: {shape}")


def _single_shape_scene(
    shape: str,
    color: Color,
    center: tuple[int, int],
    *,
    size: int,
    background: Color | None = None,
) -> Canvas:
    canvas = _canvas(background)
    _draw_shape(
        canvas,
        shape,
        center[0],
        center[1],
        color,
        size=size,
    )
    return canvas


def _clutter_scene(
    shape: str,
    color: Color,
    center: tuple[int, int],
) -> Canvas:
    canvas = _canvas()
    distractors = (
        ("circle", 35, 35),
        ("square", 90, 40),
        ("triangle", 150, 38),
        ("circle", 215, 38),
        ("square", 280, 38),
        ("triangle", 38, 120),
        ("circle", 110, 120),
        ("square", 210, 120),
        ("triangle", 282, 120),
        ("square", 38, 202),
        ("circle", 105, 200),
        ("triangle", 165, 200),
        ("square", 225, 200),
        ("circle", 282, 202),
    )
    for distractor_shape, x, y in distractors:
        if abs(x - center[0]) < 35 and abs(y - center[1]) < 35:
            continue
        _draw_shape(
            canvas,
            distractor_shape,
            x,
            y,
            NEUTRAL,
            size=13,
        )
    _draw_shape(
        canvas,
        shape,
        center[0],
        center[1],
        color,
        size=18,
    )
    return canvas


def _occluded_scene(
    shape: str,
    color: Color,
    center: tuple[int, int],
    *,
    orientation: str,
) -> Canvas:
    canvas = _canvas()
    _draw_shape(
        canvas,
        shape,
        center[0],
        center[1],
        color,
        size=34,
    )
    if orientation == "vertical":
        canvas.rectangle(
            center[0] - 7,
            center[1] - 43,
            center[0] + 7,
            center[1] + 43,
            OCCLUDER,
        )
    elif orientation == "horizontal":
        canvas.rectangle(
            center[0] - 43,
            center[1] - 7,
            center[0] + 43,
            center[1] + 7,
            OCCLUDER,
        )
    else:
        raise ValueError(f"unsupported occluder orientation: {orientation}")
    return canvas


SCENES: tuple[SceneSpec, ...] = (
    SceneSpec(
        "small-red-square-left",
        "small-object",
        "red",
        "square",
        "Which horizontal half contains the small object? Answer left or right.",
        "spatial-reasoning",
        "one word",
        "left",
        lambda: _single_shape_scene("square", RED, (45, 55), size=6),
    ),
    SceneSpec(
        "small-blue-circle-right",
        "small-object",
        "blue",
        "circle",
        "Which horizontal half contains the small object? Answer left or right.",
        "spatial-reasoning",
        "one word",
        "right",
        lambda: _single_shape_scene("circle", BLUE, (275, 178), size=7),
    ),
    SceneSpec(
        "small-green-triangle-top",
        "small-object",
        "green",
        "triangle",
        "Which vertical half contains the small object? Answer top or bottom.",
        "spatial-reasoning",
        "one word",
        "top",
        lambda: _single_shape_scene("triangle", GREEN, (160, 38), size=7),
    ),
    SceneSpec(
        "low-contrast-red-circle-left",
        "low-contrast",
        "red",
        "circle",
        "Which horizontal half contains the faint object? Answer left or right.",
        "spatial-reasoning",
        "one word",
        "left",
        lambda: _single_shape_scene(
            "circle",
            LIGHT_RED,
            (72, 120),
            size=23,
            background=(248, 226, 226),
        ),
    ),
    SceneSpec(
        "low-contrast-blue-square-right",
        "low-contrast",
        "blue",
        "square",
        "Which horizontal half contains the faint object? Answer left or right.",
        "spatial-reasoning",
        "one word",
        "right",
        lambda: _single_shape_scene(
            "square",
            LIGHT_BLUE,
            (248, 120),
            size=22,
            background=(225, 235, 248),
        ),
    ),
    SceneSpec(
        "low-contrast-green-triangle-bottom",
        "low-contrast",
        "green",
        "triangle",
        "Which vertical half contains the faint object? Answer top or bottom.",
        "spatial-reasoning",
        "one word",
        "bottom",
        lambda: _single_shape_scene(
            "triangle",
            LIGHT_GREEN,
            (160, 180),
            size=24,
            background=(228, 244, 232),
        ),
    ),
    SceneSpec(
        "clutter-purple-triangle-center",
        "visual-clutter",
        "purple",
        "triangle",
        "How many purple objects are visible? Answer with an integer.",
        "counting",
        "integer",
        1,
        lambda: _clutter_scene("triangle", PURPLE, (160, 120)),
    ),
    SceneSpec(
        "clutter-orange-circle-left",
        "visual-clutter",
        "orange",
        "circle",
        "How many orange objects are visible? Answer with an integer.",
        "counting",
        "integer",
        1,
        lambda: _clutter_scene("circle", ORANGE, (70, 120)),
    ),
    SceneSpec(
        "clutter-green-square-right",
        "visual-clutter",
        "green",
        "square",
        "How many green objects are visible? Answer with an integer.",
        "counting",
        "integer",
        1,
        lambda: _clutter_scene("square", GREEN, (250, 120)),
    ),
    SceneSpec(
        "occluded-red-circle-vertical",
        "partial-occlusion",
        "red",
        "circle",
        "Is the gray occluding bar vertical or horizontal? Answer with one word.",
        "occlusion-reasoning",
        "one word",
        "vertical",
        lambda: _occluded_scene(
            "circle",
            RED,
            (80, 120),
            orientation="vertical",
        ),
    ),
    SceneSpec(
        "occluded-blue-square-horizontal",
        "partial-occlusion",
        "blue",
        "square",
        "Is the gray occluding bar vertical or horizontal? Answer with one word.",
        "occlusion-reasoning",
        "one word",
        "horizontal",
        lambda: _occluded_scene(
            "square",
            BLUE,
            (240, 120),
            orientation="horizontal",
        ),
    ),
    SceneSpec(
        "occluded-green-triangle-vertical",
        "partial-occlusion",
        "green",
        "triangle",
        "How many gray bars occlude the colored shape? Answer with an integer.",
        "occlusion-reasoning",
        "integer",
        1,
        lambda: _occluded_scene(
            "triangle",
            GREEN,
            (160, 120),
            orientation="vertical",
        ),
    ),
)


def generate_assets(
    output_dir: Path,
    *,
    review_sheet: Path | None = None,
) -> list[Path]:
    generated: list[Path] = []
    canvases: list[Canvas] = []
    for scene in SCENES:
        canvas = scene.renderer()
        output_path = output_dir / f"{scene.key}.png"
        canvas.write_png(output_path)
        canvases.append(canvas)
        generated.append(output_path)
    if review_sheet is not None:
        write_review_sheet(review_sheet, canvases)
        generated.append(review_sheet)
    return generated


def write_review_sheet(path: Path, canvases: Sequence[Canvas]) -> None:
    """Write a full-resolution 3-column sheet in stable scene order."""

    if len(canvases) != len(SCENES):
        raise ValueError(
            f"review sheet requires {len(SCENES)} canvases; "
            f"got {len(canvases)}"
        )
    columns = 3
    rows = 4
    margin = 2
    sheet = Canvas(
        WIDTH * columns + margin * (columns + 1),
        HEIGHT * rows + margin * (rows + 1),
    )
    for index, canvas in enumerate(canvases):
        column = index % columns
        row = index // columns
        left = margin + column * (WIDTH + margin)
        top = margin + row * (HEIGHT + margin)
        for row_index in range(HEIGHT):
            source_start = row_index * WIDTH * 3
            source_end = source_start + WIDTH * 3
            target_start = ((top + row_index) * sheet.width + left) * 3
            sheet.pixels[
                target_start : target_start + WIDTH * 3
            ] = canvas.pixels[source_start:source_end]
    sheet.write_png(path)


def _normalize_media_prefix(media_prefix: str) -> str:
    normalized = media_prefix.strip().replace("\\", "/").rstrip("/")
    if not normalized:
        raise ValueError("media_prefix must be a non-empty relative path")
    prefix_path = Path(normalized)
    if prefix_path.is_absolute() or ":" in normalized or ".." in prefix_path.parts:
        raise ValueError("media_prefix must be relative and portable")
    return normalized


def _task_row(
    *,
    task_id: str,
    scene: SceneSpec,
    prompt: str,
    category: str,
    answer_format: str,
    answer: str | int,
    dataset_version: str,
    media_prefix: str,
) -> dict[str, Any]:
    numeric = isinstance(answer, int)
    scoring: dict[str, Any] = (
        {
            "type": "numeric_tolerance",
            "target": answer,
            "absolute_tolerance": 0,
        }
        if numeric
        else {"type": "normalized_exact_match"}
    )
    return {
        "schema_version": "1.2",
        "id": task_id,
        "prompt": prompt,
        "media": [f"{media_prefix}/{scene.key}.png"],
        "expected_keywords": [] if numeric else [str(answer)],
        "scoring": scoring,
        "metadata": {
            "dataset_version": dataset_version,
            "category": category,
            "language": "en",
            "difficulty": "intermediate",
            "answer_format": answer_format,
            "robustness_factor": scene.factor,
            "source": "project-generated",
            "generator": GENERATOR_REFERENCE,
            "license": "Apache-2.0",
        },
    }


def build_tasks(
    dataset_version: str,
    media_prefix: str,
) -> list[dict[str, Any]]:
    version = dataset_version.strip()
    if not version:
        raise ValueError("dataset_version must be a non-empty string")
    prefix = _normalize_media_prefix(media_prefix)
    tasks: list[dict[str, Any]] = []
    for scene in SCENES:
        tasks.extend(
            (
                _task_row(
                    task_id=f"{scene.key}-color",
                    scene=scene,
                    prompt=(
                        "What color is the target object? "
                        "Answer with one word."
                    ),
                    category="attribute-recognition",
                    answer_format="one word",
                    answer=scene.color_name,
                    dataset_version=version,
                    media_prefix=prefix,
                ),
                _task_row(
                    task_id=f"{scene.key}-shape",
                    scene=scene,
                    prompt=(
                        "What shape is the target colored object? "
                        "Answer with one word."
                    ),
                    category="attribute-recognition",
                    answer_format="one word",
                    answer=scene.shape_name,
                    dataset_version=version,
                    media_prefix=prefix,
                ),
                _task_row(
                    task_id=f"{scene.key}-context",
                    scene=scene,
                    prompt=scene.context_prompt,
                    category=scene.context_category,
                    answer_format=scene.context_format,
                    answer=scene.context_answer,
                    dataset_version=version,
                    media_prefix=prefix,
                ),
            )
        )
    return tasks


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_review_template(
    path: Path,
    *,
    dataset_path: Path,
    dataset_version: str,
    tasks: Sequence[dict[str, Any]],
) -> None:
    version = dataset_version.strip()
    if not version:
        raise ValueError("dataset_version must be a non-empty string")
    media_order = list(
        dict.fromkeys(
            media_item
            for task in tasks
            for media_item in task["media"]
        )
    )
    template = {
        "schema_version": "1.1",
        "review_profile": REVIEW_PROFILE,
        "dataset_version": version,
        "dataset_sha256": _sha256(dataset_path),
        "review_media_order": media_order,
        "entries": [
            {
                "task_id": task["id"],
                "media": task["media"],
                "checks": {check: False for check in REVIEW_CHECKS},
                "reviewer": None,
                "reviewed_at": None,
                "notes": "",
            }
            for task in tasks
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--review-sheet", type=Path)
    parser.add_argument("--dataset-output", type=Path)
    parser.add_argument("--dataset-version")
    parser.add_argument("--media-prefix")
    parser.add_argument("--review-output", type=Path)
    args = parser.parse_args()

    draft_arguments = (
        args.dataset_output,
        args.dataset_version,
        args.media_prefix,
    )
    if any(value is not None for value in draft_arguments) and not all(
        value is not None for value in draft_arguments
    ):
        parser.error(
            "--dataset-output, --dataset-version, and --media-prefix must "
            "be supplied together"
        )
    if args.review_output is not None and args.dataset_output is None:
        parser.error("--review-output requires a dataset draft")

    generated = generate_assets(
        args.output_dir,
        review_sheet=args.review_sheet,
    )
    print(f"Generated {len(generated)} deterministic image/review assets")

    if args.dataset_output is not None:
        tasks = build_tasks(args.dataset_version, args.media_prefix)
        write_jsonl(args.dataset_output, tasks)
        print(f"Wrote {len(tasks)} draft tasks to {args.dataset_output}")
        if args.review_output is not None:
            write_review_template(
                args.review_output,
                dataset_path=args.dataset_output,
                dataset_version=args.dataset_version,
                tasks=tasks,
            )
            print(f"Wrote incomplete review template to {args.review_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

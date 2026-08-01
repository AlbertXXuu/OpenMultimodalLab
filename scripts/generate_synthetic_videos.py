"""Generate deterministic short-video assets and an optional task draft."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
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


WIDTH = 160
HEIGHT = 120
FPS = 8
FRAME_COUNT = 16
SAMPLED_FRAME_INDICES = (0, 2, 4, 6, 8, 10, 12, 14)
GENERATOR_REFERENCE = "scripts/generate_synthetic_videos.py"
REVIEW_CHECKS = (
    "media_opens_and_plays",
    "sampled_temporal_evidence_visible",
    "prompt_answer_matches_media",
    "answer_is_unambiguous",
    "license_and_provenance_confirmed",
)

Frame = bytes
FrameRenderer = Callable[[], list[Frame]]


@dataclass(frozen=True, slots=True)
class ClipSpec:
    """One stable video asset definition."""

    key: str
    renderer: FrameRenderer


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """One task whose public dataset version is supplied by the caller."""

    task_id: str
    clip_key: str
    prompt: str
    category: str
    answer_format: str
    difficulty: str
    answer: str | int


def _draw_shape(
    canvas: Canvas,
    shape: str,
    center_x: int,
    center_y: int,
    color: Color,
) -> None:
    if shape == "square":
        canvas.rectangle(
            center_x - 12,
            center_y - 12,
            center_x + 12,
            center_y + 12,
            color,
        )
        return
    if shape == "circle":
        canvas.circle(center_x, center_y, 12, color)
        return
    if shape == "triangle":
        canvas.triangle(
            (
                (center_x, center_y - 14),
                (center_x - 14, center_y + 12),
                (center_x + 14, center_y + 12),
            ),
            color,
        )
        return
    raise ValueError(f"unsupported video shape: {shape}")


def _frame(draw: Callable[[Canvas], None]) -> Frame:
    canvas = Canvas(WIDTH, HEIGHT)
    draw(canvas)
    return bytes(canvas.pixels)


def _moving_clip(
    shape: str,
    color: Color,
    start: tuple[int, int],
    end: tuple[int, int],
) -> list[Frame]:
    frames: list[Frame] = []
    for index in range(FRAME_COUNT):
        x = start[0] + (end[0] - start[0]) * index // (FRAME_COUNT - 1)
        y = start[1] + (end[1] - start[1]) * index // (FRAME_COUNT - 1)
        frames.append(
            _frame(
                lambda canvas, x=x, y=y: _draw_shape(
                    canvas,
                    shape,
                    x,
                    y,
                    color,
                )
            )
        )
    return frames


def _appearance_clip() -> list[Frame]:
    frames: list[Frame] = []
    for index in range(FRAME_COUNT):
        def draw(canvas: Canvas, index: int = index) -> None:
            if index >= 2:
                _draw_shape(canvas, "circle", 50, 60, RED)
            if index >= 8:
                _draw_shape(canvas, "square", 110, 60, BLUE)

        frames.append(_frame(draw))
    return frames


def _disappearance_clip() -> list[Frame]:
    frames: list[Frame] = []
    for index in range(FRAME_COUNT):
        def draw(canvas: Canvas, index: int = index) -> None:
            if index < 6:
                _draw_shape(canvas, "triangle", 50, 60, GREEN)
            if index < 12:
                _draw_shape(canvas, "square", 110, 60, ORANGE)

        frames.append(_frame(draw))
    return frames


def _color_change_clip() -> list[Frame]:
    return [
        _frame(
            lambda canvas, index=index: _draw_shape(
                canvas,
                "square",
                80,
                60,
                RED if index < 8 else BLUE,
            )
        )
        for index in range(FRAME_COUNT)
    ]


def _count_increase_clip() -> list[Frame]:
    frames: list[Frame] = []
    for index in range(FRAME_COUNT):
        def draw(canvas: Canvas, index: int = index) -> None:
            centers = [80]
            if index >= 6:
                centers.insert(0, 45)
            if index >= 11:
                centers.append(115)
            for center_x in centers:
                _draw_shape(canvas, "circle", center_x, 60, PURPLE)

        frames.append(_frame(draw))
    return frames


CLIPS: tuple[ClipSpec, ...] = (
    ClipSpec(
        "motion-right-red-square",
        lambda: _moving_clip("square", RED, (24, 60), (136, 60)),
    ),
    ClipSpec(
        "motion-left-blue-circle",
        lambda: _moving_clip("circle", BLUE, (136, 60), (24, 60)),
    ),
    ClipSpec(
        "motion-down-green-triangle",
        lambda: _moving_clip("triangle", GREEN, (80, 24), (80, 96)),
    ),
    ClipSpec(
        "motion-up-purple-square",
        lambda: _moving_clip("square", PURPLE, (80, 96), (80, 24)),
    ),
    ClipSpec("event-appearance-order", _appearance_clip),
    ClipSpec("event-disappearance-order", _disappearance_clip),
    ClipSpec("state-color-change", _color_change_clip),
    ClipSpec("count-increase", _count_increase_clip),
)


TASKS: tuple[TaskSpec, ...] = (
    TaskSpec(
        "video-right-direction",
        CLIPS[0].key,
        "Which direction does the red square move? Answer with one word.",
        "motion-direction",
        "one word",
        "basic",
        "right",
    ),
    TaskSpec(
        "video-right-start",
        CLIPS[0].key,
        "On which side does the red square start? Answer with one word.",
        "temporal-position",
        "one word",
        "basic",
        "left",
    ),
    TaskSpec(
        "video-right-end",
        CLIPS[0].key,
        "On which side does the red square end? Answer with one word.",
        "temporal-position",
        "one word",
        "basic",
        "right",
    ),
    TaskSpec(
        "video-left-direction",
        CLIPS[1].key,
        "Which direction does the blue circle move? Answer with one word.",
        "motion-direction",
        "one word",
        "basic",
        "left",
    ),
    TaskSpec(
        "video-left-start",
        CLIPS[1].key,
        "On which side does the blue circle start? Answer with one word.",
        "temporal-position",
        "one word",
        "basic",
        "right",
    ),
    TaskSpec(
        "video-left-end",
        CLIPS[1].key,
        "On which side does the blue circle end? Answer with one word.",
        "temporal-position",
        "one word",
        "basic",
        "left",
    ),
    TaskSpec(
        "video-down-direction",
        CLIPS[2].key,
        "Which direction does the green triangle move? Answer with one word.",
        "motion-direction",
        "one word",
        "basic",
        "down",
    ),
    TaskSpec(
        "video-down-start",
        CLIPS[2].key,
        "Where does the green triangle start vertically? Answer top or bottom.",
        "temporal-position",
        "one word",
        "basic",
        "top",
    ),
    TaskSpec(
        "video-down-end",
        CLIPS[2].key,
        "Where does the green triangle end vertically? Answer top or bottom.",
        "temporal-position",
        "one word",
        "basic",
        "bottom",
    ),
    TaskSpec(
        "video-up-direction",
        CLIPS[3].key,
        "Which direction does the purple square move? Answer with one word.",
        "motion-direction",
        "one word",
        "basic",
        "up",
    ),
    TaskSpec(
        "video-up-start",
        CLIPS[3].key,
        "Where does the purple square start vertically? Answer top or bottom.",
        "temporal-position",
        "one word",
        "basic",
        "bottom",
    ),
    TaskSpec(
        "video-up-end",
        CLIPS[3].key,
        "Where does the purple square end vertically? Answer top or bottom.",
        "temporal-position",
        "one word",
        "basic",
        "top",
    ),
    TaskSpec(
        "video-appear-first",
        CLIPS[4].key,
        "Which object appears first? Answer with its color and shape.",
        "event-order",
        "short phrase",
        "intermediate",
        "red circle",
    ),
    TaskSpec(
        "video-appear-second",
        CLIPS[4].key,
        "Which object appears second? Answer with its color and shape.",
        "event-order",
        "short phrase",
        "intermediate",
        "blue square",
    ),
    TaskSpec(
        "video-appear-final-count",
        CLIPS[4].key,
        "How many objects are visible at the end? Answer with an integer.",
        "temporal-counting",
        "integer",
        "basic",
        2,
    ),
    TaskSpec(
        "video-disappear-first",
        CLIPS[5].key,
        "Which object disappears first? Answer with its color and shape.",
        "event-order",
        "short phrase",
        "intermediate",
        "green triangle",
    ),
    TaskSpec(
        "video-disappear-last",
        CLIPS[5].key,
        "Which object disappears last? Answer with its color and shape.",
        "event-order",
        "short phrase",
        "intermediate",
        "orange square",
    ),
    TaskSpec(
        "video-disappear-final-count",
        CLIPS[5].key,
        "How many objects are visible at the end? Answer with an integer.",
        "temporal-counting",
        "integer",
        "basic",
        0,
    ),
    TaskSpec(
        "video-color-start",
        CLIPS[6].key,
        "What color is the square at the beginning? Answer with one word.",
        "state-change",
        "one word",
        "basic",
        "red",
    ),
    TaskSpec(
        "video-color-end",
        CLIPS[6].key,
        "What color is the square at the end? Answer with one word.",
        "state-change",
        "one word",
        "basic",
        "blue",
    ),
    TaskSpec(
        "video-color-changed",
        CLIPS[6].key,
        "Does the square change color? Answer yes or no.",
        "state-change",
        "yes or no",
        "basic",
        "yes",
    ),
    TaskSpec(
        "video-count-start",
        CLIPS[7].key,
        "How many circles are visible at the beginning? Answer with an integer.",
        "temporal-counting",
        "integer",
        "basic",
        1,
    ),
    TaskSpec(
        "video-count-end",
        CLIPS[7].key,
        "How many circles are visible at the end? Answer with an integer.",
        "temporal-counting",
        "integer",
        "basic",
        3,
    ),
    TaskSpec(
        "video-count-added",
        CLIPS[7].key,
        "How many circles are added from beginning to end? Answer with an integer.",
        "temporal-counting",
        "integer",
        "intermediate",
        2,
    ),
)


def _chunk(chunk_id: bytes, payload: bytes) -> bytes:
    if len(chunk_id) != 4:
        raise ValueError("AVI chunk identifiers must contain four bytes")
    padding = b"\x00" if len(payload) % 2 else b""
    return chunk_id + struct.pack("<I", len(payload)) + payload + padding


def _list_chunk(list_type: bytes, payload: bytes) -> bytes:
    return _chunk(b"LIST", list_type + payload)


def _dib_frame(rgb: Frame) -> bytes:
    expected_bytes = WIDTH * HEIGHT * 3
    if len(rgb) != expected_bytes:
        raise ValueError(
            f"frame must contain {expected_bytes} RGB bytes; got {len(rgb)}"
        )
    source_stride = WIDTH * 3
    output_stride = (source_stride + 3) & ~3
    encoded = bytearray()
    for y in range(HEIGHT - 1, -1, -1):
        row = rgb[y * source_stride : (y + 1) * source_stride]
        bgr = bytearray(source_stride)
        bgr[0::3] = row[2::3]
        bgr[1::3] = row[1::3]
        bgr[2::3] = row[0::3]
        encoded.extend(bgr)
        encoded.extend(b"\x00" * (output_stride - source_stride))
    return bytes(encoded)


def avi_bytes(frames: Sequence[Frame]) -> bytes:
    """Encode deterministic uncompressed 24-bit AVI/DIB bytes."""

    if len(frames) != FRAME_COUNT:
        raise ValueError(
            f"clip must contain exactly {FRAME_COUNT} frames; got {len(frames)}"
        )
    encoded_frames = [_dib_frame(frame) for frame in frames]
    frame_bytes = len(encoded_frames[0])
    microseconds_per_frame = 1_000_000 // FPS

    main_header = struct.pack(
        "<IIIIIIIIII4I",
        microseconds_per_frame,
        frame_bytes * FPS,
        0,
        0x10,
        FRAME_COUNT,
        0,
        1,
        frame_bytes,
        WIDTH,
        HEIGHT,
        0,
        0,
        0,
        0,
    )
    stream_header = struct.pack(
        "<4s4sIHHIIIIIIIIhhhh",
        b"vids",
        b"DIB ",
        0,
        0,
        0,
        0,
        1,
        FPS,
        0,
        FRAME_COUNT,
        frame_bytes,
        0xFFFFFFFF,
        0,
        0,
        0,
        WIDTH,
        HEIGHT,
    )
    bitmap_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        WIDTH,
        HEIGHT,
        1,
        24,
        0,
        frame_bytes,
        0,
        0,
        0,
        0,
    )
    stream_list = _list_chunk(
        b"strl",
        _chunk(b"strh", stream_header) + _chunk(b"strf", bitmap_header),
    )
    header_list = _list_chunk(
        b"hdrl",
        _chunk(b"avih", main_header) + stream_list,
    )

    movie_payload = bytearray()
    index_payload = bytearray()
    for frame in encoded_frames:
        offset = 4 + len(movie_payload)
        movie_payload.extend(_chunk(b"00db", frame))
        index_payload.extend(
            struct.pack("<4sIII", b"00db", 0x10, offset, len(frame))
        )
    movie_list = _list_chunk(b"movi", bytes(movie_payload))
    index_chunk = _chunk(b"idx1", bytes(index_payload))
    payload = b"AVI " + header_list + movie_list + index_chunk
    return b"RIFF" + struct.pack("<I", len(payload)) + payload


def write_avi(path: Path, frames: Sequence[Frame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(avi_bytes(frames))


def write_review_sheet(path: Path, frames: Sequence[Frame]) -> None:
    """Write a 2x2 contact sheet ordered top-left to bottom-right."""

    margin = 2
    sheet = Canvas(WIDTH * 2 + margin * 3, HEIGHT * 2 + margin * 3)
    positions = (
        (margin, margin),
        (WIDTH + margin * 2, margin),
        (margin, HEIGHT + margin * 2),
        (WIDTH + margin * 2, HEIGHT + margin * 2),
    )
    for frame_index, (left, top) in zip(
        (0, 5, 10, 15),
        positions,
        strict=True,
    ):
        frame = frames[frame_index]
        for row_index in range(HEIGHT):
            source_start = row_index * WIDTH * 3
            source_end = source_start + WIDTH * 3
            target_start = ((top + row_index) * sheet.width + left) * 3
            sheet.pixels[
                target_start : target_start + WIDTH * 3
            ] = frame[source_start:source_end]
    sheet.write_png(path)


def generate_assets(
    output_dir: Path,
    *,
    review_dir: Path | None = None,
) -> list[Path]:
    generated: list[Path] = []
    for clip in CLIPS:
        frames = clip.renderer()
        video_path = output_dir / f"{clip.key}.avi"
        write_avi(video_path, frames)
        generated.append(video_path)
        if review_dir is not None:
            review_path = review_dir / f"{clip.key}.png"
            write_review_sheet(review_path, frames)
            generated.append(review_path)
    return generated


def build_tasks(
    dataset_version: str,
    media_prefix: str,
) -> list[dict[str, Any]]:
    if not dataset_version.strip():
        raise ValueError("dataset_version must be a non-empty string")
    normalized_prefix = media_prefix.strip().replace("\\", "/").rstrip("/")
    if not normalized_prefix:
        raise ValueError("media_prefix must be a non-empty relative path")
    prefix_path = Path(normalized_prefix)
    if (
        prefix_path.is_absolute()
        or ":" in normalized_prefix
        or ".." in prefix_path.parts
    ):
        raise ValueError("media_prefix must be relative and portable")

    tasks: list[dict[str, Any]] = []
    for spec in TASKS:
        numeric = isinstance(spec.answer, int)
        expected_keywords = [] if numeric else [str(spec.answer)]
        scoring: dict[str, Any] = (
            {
                "type": "numeric_tolerance",
                "target": spec.answer,
                "absolute_tolerance": 0,
            }
            if numeric
            else {"type": "normalized_exact_match"}
        )
        tasks.append(
            {
                "schema_version": "1.2",
                "id": spec.task_id,
                "prompt": spec.prompt,
                "media": [f"{normalized_prefix}/{spec.clip_key}.avi"],
                "expected_keywords": expected_keywords,
                "scoring": scoring,
                "metadata": {
                    "dataset_version": dataset_version.strip(),
                    "category": spec.category,
                    "language": "en",
                    "difficulty": spec.difficulty,
                    "answer_format": spec.answer_format,
                    "source": "project-generated",
                    "generator": GENERATOR_REFERENCE,
                    "license": "Apache-2.0",
                },
            }
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
    template = {
        "schema_version": "1.0",
        "dataset_version": version,
        "dataset_sha256": _sha256(dataset_path),
        "sampled_frame_indices": list(SAMPLED_FRAME_INDICES),
        "contact_sheet_order": [0, 5, 10, 15],
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
    parser.add_argument("--review-dir", type=Path)
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
        review_dir=args.review_dir,
    )
    print(f"Generated {len(generated)} deterministic video/review assets")

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

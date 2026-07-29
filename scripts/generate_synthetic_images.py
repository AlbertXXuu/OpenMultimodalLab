"""Generate the deterministic PNG assets used by the synthetic-v1 task set."""

from __future__ import annotations

import argparse
import struct
import zlib
from collections.abc import Callable, Sequence
from pathlib import Path

Color = tuple[int, int, int]
Point = tuple[int, int]

WIDTH = 320
HEIGHT = 240
BACKGROUND: Color = (248, 250, 252)

RED: Color = (239, 68, 68)
BLUE: Color = (59, 130, 246)
GREEN: Color = (34, 197, 94)
ORANGE: Color = (249, 115, 22)
PURPLE: Color = (168, 85, 247)
YELLOW: Color = (234, 179, 8)


class Canvas:
    """Small RGB raster canvas with deterministic shape primitives."""

    def __init__(self, width: int = WIDTH, height: int = HEIGHT) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray(BACKGROUND * (width * height))

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        offset = (y * self.width + x) * 3
        self.pixels[offset : offset + 3] = bytes(color)

    def rectangle(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        color: Color,
    ) -> None:
        for y in range(max(0, top), min(self.height, bottom)):
            for x in range(max(0, left), min(self.width, right)):
                self.set_pixel(x, y, color)

    def circle(self, center_x: int, center_y: int, radius: int, color: Color) -> None:
        radius_squared = radius * radius
        for y in range(center_y - radius, center_y + radius + 1):
            for x in range(center_x - radius, center_x + radius + 1):
                if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius_squared:
                    self.set_pixel(x, y, color)

    def triangle(self, points: Sequence[Point], color: Color) -> None:
        if len(points) != 3:
            raise ValueError("A triangle requires exactly three points")

        (x1, y1), (x2, y2), (x3, y3) = points
        min_x = max(0, min(x1, x2, x3))
        max_x = min(self.width - 1, max(x1, x2, x3))
        min_y = max(0, min(y1, y2, y3))
        max_y = min(self.height - 1, max(y1, y2, y3))

        def edge(a: Point, b: Point, point: Point) -> int:
            return (
                (point[0] - a[0]) * (b[1] - a[1])
                - (point[1] - a[1]) * (b[0] - a[0])
            )

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                point = (x, y)
                edges = (
                    edge((x1, y1), (x2, y2), point),
                    edge((x2, y2), (x3, y3), point),
                    edge((x3, y3), (x1, y1), point),
                )
                if all(value >= 0 for value in edges) or all(
                    value <= 0 for value in edges
                ):
                    self.set_pixel(x, y, color)

    def write_png(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        stride = self.width * 3
        raw_rows = b"".join(
            b"\x00" + bytes(self.pixels[offset : offset + stride])
            for offset in range(0, len(self.pixels), stride)
        )

        def chunk(chunk_type: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + chunk_type
                + data
                + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
            )

        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0),
            )
            + chunk(b"IDAT", zlib.compress(raw_rows, level=9))
            + chunk(b"IEND", b"")
        )
        path.write_bytes(png)


def scene_basic_pair(canvas: Canvas) -> None:
    canvas.circle(90, 120, 45, RED)
    canvas.rectangle(195, 75, 285, 165, BLUE)


def scene_above_below(canvas: Canvas) -> None:
    canvas.triangle(((160, 25), (105, 105), (215, 105)), GREEN)
    canvas.rectangle(100, 150, 220, 205, ORANGE)


def scene_three_circles(canvas: Canvas) -> None:
    for center_x in (75, 160, 245):
        canvas.circle(center_x, 120, 28, PURPLE)


def scene_five_squares(canvas: Canvas) -> None:
    for center_x in (40, 100, 160, 220, 280):
        canvas.rectangle(center_x - 18, 102, center_x + 18, 138, BLUE)


def scene_left_right(canvas: Canvas) -> None:
    canvas.circle(80, 120, 40, RED)
    canvas.triangle(((240, 70), (195, 165), (285, 165)), BLUE)


def scene_below(canvas: Canvas) -> None:
    canvas.circle(160, 70, 35, GREEN)
    canvas.rectangle(120, 145, 200, 205, YELLOW)


def scene_three_shapes(canvas: Canvas) -> None:
    canvas.circle(55, 120, 32, BLUE)
    canvas.triangle(((160, 75), (120, 165), (200, 165)), YELLOW)
    canvas.rectangle(235, 90, 295, 150, GREEN)


def scene_two_rectangles(canvas: Canvas) -> None:
    canvas.rectangle(45, 80, 130, 160, ORANGE)
    canvas.rectangle(190, 80, 275, 160, ORANGE)


def scene_between(canvas: Canvas) -> None:
    canvas.rectangle(35, 85, 105, 155, RED)
    canvas.triangle(((160, 70), (120, 165), (200, 165)), PURPLE)
    canvas.circle(265, 120, 38, BLUE)


def scene_size_comparison(canvas: Canvas) -> None:
    canvas.circle(90, 120, 55, RED)
    canvas.circle(240, 120, 27, RED)


SCENES: tuple[tuple[str, Callable[[Canvas], None]], ...] = (
    ("shapes-basic-001.png", scene_basic_pair),
    ("spatial-above-001.png", scene_above_below),
    ("counting-circles-001.png", scene_three_circles),
    ("counting-squares-001.png", scene_five_squares),
    ("spatial-left-001.png", scene_left_right),
    ("spatial-below-001.png", scene_below),
    ("shapes-multi-001.png", scene_three_shapes),
    ("counting-rectangles-001.png", scene_two_rectangles),
    ("spatial-between-001.png", scene_between),
    ("comparison-size-001.png", scene_size_comparison),
)


def generate(output_dir: Path) -> list[Path]:
    generated: list[Path] = []
    for filename, draw_scene in SCENES:
        canvas = Canvas()
        draw_scene(canvas)
        output_path = output_dir / filename
        canvas.write_png(output_path)
        generated.append(output_path)
    return generated


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "examples" / "assets" / "synthetic-v1",
    )
    args = parser.parse_args()

    generated = generate(args.output_dir)
    print(f"Generated {len(generated)} PNG files in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

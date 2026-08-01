"""Generate deterministic document, table, and chart PNG benchmark assets."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path

from generate_synthetic_images import Canvas, Color


WIDTH = 768
HEIGHT = 512

INK: Color = (15, 23, 42)
MUTED: Color = (71, 85, 105)
LINE: Color = (203, 213, 225)
PAPER: Color = (255, 255, 255)
PALE: Color = (241, 245, 249)
BLUE: Color = (37, 99, 235)
TEAL: Color = (13, 148, 136)
GREEN: Color = (22, 163, 74)
AMBER: Color = (217, 119, 6)
RED: Color = (220, 38, 38)
PURPLE: Color = (124, 58, 237)


FONT: dict[str, tuple[str, ...]] = {
    " ": ("00000",) * 7,
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
}


class DocumentCanvas(Canvas):
    """Canvas with deterministic bitmap typography and line primitives."""

    def rectangle(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        color: Color,
    ) -> None:
        left = max(0, left)
        right = min(self.width, right)
        row = bytes(color) * max(0, right - left)
        for y in range(max(0, top), min(self.height, bottom)):
            offset = (y * self.width + left) * 3
            self.pixels[offset : offset + len(row)] = row

    def text(self, x: int, y: int, value: str, scale: int = 2, color: Color = INK) -> None:
        cursor = x
        for character in value.upper():
            glyph = FONT.get(character)
            if glyph is None:
                raise ValueError(f"unsupported bitmap-font character: {character!r}")
            for row_index, row in enumerate(glyph):
                for column_index, pixel in enumerate(row):
                    if pixel == "1":
                        self.rectangle(
                            cursor + column_index * scale,
                            y + row_index * scale,
                            cursor + (column_index + 1) * scale,
                            y + (row_index + 1) * scale,
                            color,
                        )
            cursor += 6 * scale

    def line(self, start: tuple[int, int], end: tuple[int, int], color: Color, width: int = 2) -> None:
        x1, y1 = start
        x2, y2 = end
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        step_x = 1 if x1 < x2 else -1
        step_y = 1 if y1 < y2 else -1
        error = dx + dy
        while True:
            self.rectangle(x1, y1, x1 + width, y1 + width, color)
            if x1 == x2 and y1 == y2:
                break
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x1 += step_x
            if doubled <= dx:
                error += dx
                y1 += step_y


def base_document(title: str, accent: Color = BLUE) -> DocumentCanvas:
    canvas = DocumentCanvas(WIDTH, HEIGHT)
    canvas.rectangle(28, 24, 744, 496, (226, 232, 240))
    canvas.rectangle(20, 16, 736, 488, PAPER)
    canvas.rectangle(20, 16, 32, 488, accent)
    canvas.text(56, 42, title, 4, INK)
    canvas.rectangle(56, 82, 704, 86, accent)
    return canvas


def label_value(canvas: DocumentCanvas, y: int, label: str, value: str, accent: Color = BLUE) -> None:
    canvas.rectangle(64, y, 70, y + 14, accent)
    canvas.text(82, y, label, 2, MUTED)
    canvas.text(324, y, value, 2, INK)
    canvas.rectangle(64, y + 22, 688, y + 24, PALE)


def receipt(canvas: DocumentCanvas) -> None:
    canvas.text(580, 46, "R-2048", 2, MUTED)
    canvas.text(62, 108, "ITEM", 2, MUTED)
    canvas.text(570, 108, "PRICE", 2, MUTED)
    rows = (("LATTE", "$4.50"), ("BAGEL", "$3.25"), ("TAX", "$0.62"))
    for index, (item, price) in enumerate(rows):
        y = 150 + index * 52
        canvas.text(62, y, item, 3, INK)
        canvas.text(570, y, price, 3, INK)
        canvas.rectangle(62, y + 28, 688, y + 30, PALE)
    canvas.rectangle(52, 326, 700, 390, (239, 246, 255))
    canvas.text(70, 347, "TOTAL", 3, BLUE)
    canvas.text(550, 347, "$8.37", 3, BLUE)
    canvas.text(62, 430, "DATE 2026-07-18", 2, MUTED)


def invoice(canvas: DocumentCanvas) -> None:
    label_value(canvas, 110, "INVOICE", "INV-731", PURPLE)
    label_value(canvas, 152, "CLIENT", "NOVA LABS", PURPLE)
    label_value(canvas, 208, "DESIGN", "$240.00", PURPLE)
    label_value(canvas, 250, "HOSTING", "$60.00", PURPLE)
    label_value(canvas, 292, "TAX", "$24.00", PURPLE)
    canvas.rectangle(52, 342, 700, 410, (245, 243, 255))
    canvas.text(70, 365, "AMOUNT DUE", 3, PURPLE)
    canvas.text(520, 365, "$324.00", 3, PURPLE)
    canvas.text(62, 438, "DUE 2026-08-15", 2, MUTED)


def schedule(canvas: DocumentCanvas) -> None:
    canvas.text(590, 48, "ROOM A", 2, MUTED)
    canvas.text(62, 110, "TIME", 2, MUTED)
    canvas.text(240, 110, "EVENT", 2, MUTED)
    rows = (("09:00", "VISION LAB"), ("10:30", "DATA REVIEW"), ("13:15", "ROBOTICS"), ("15:00", "DEMO"))
    colors = (BLUE, TEAL, AMBER, PURPLE)
    for index, ((time, event), color) in enumerate(zip(rows, colors, strict=True)):
        y = 154 + index * 66
        canvas.rectangle(54, y - 12, 700, y + 38, PALE)
        canvas.rectangle(54, y - 12, 64, y + 38, color)
        canvas.text(84, y, time, 3, INK)
        canvas.text(270, y, event, 3, INK)


def draw_table(canvas: DocumentCanvas, headers: Sequence[str], rows: Sequence[Sequence[str]], widths: Sequence[int]) -> None:
    left = 52
    top = 112
    row_height = 58
    positions = [left]
    for width in widths:
        positions.append(positions[-1] + width)
    canvas.rectangle(left, top, positions[-1], top + row_height, INK)
    for column, header in enumerate(headers):
        canvas.text(positions[column] + 14, top + 20, header, 2, PAPER)
    for row_index, row in enumerate(rows):
        y = top + (row_index + 1) * row_height
        canvas.rectangle(left, y, positions[-1], y + row_height, PAPER if row_index % 2 == 0 else PALE)
        for column, value in enumerate(row):
            canvas.text(positions[column] + 14, y + 20, value, 2, INK)
    for x in positions:
        canvas.rectangle(x, top, x + 2, top + row_height * (len(rows) + 1), LINE)
    for row_index in range(len(rows) + 2):
        y = top + row_index * row_height
        canvas.rectangle(left, y, positions[-1], y + 2, LINE)


def inventory(canvas: DocumentCanvas) -> None:
    draw_table(
        canvas,
        ("PRODUCT", "Q1", "Q2", "STOCK"),
        (("ALPHA", "120", "150", "32"), ("BETA", "90", "135", "18"), ("GAMMA", "160", "140", "24"), ("DELTA", "110", "170", "11")),
        (260, 120, 120, 140),
    )


def bar_chart(canvas: DocumentCanvas) -> None:
    values = (("NORTH", 40, BLUE), ("SOUTH", 65, TEAL), ("EAST", 55, AMBER), ("WEST", 30, PURPLE))
    baseline = 400
    canvas.line((82, 120), (82, baseline), INK)
    canvas.line((82, baseline), (704, baseline), INK)
    for tick in (0, 20, 40, 60):
        y = baseline - tick * 4
        canvas.text(42, y - 7, str(tick), 1, MUTED)
        canvas.rectangle(82, y, 704, y + 1, LINE)
    for index, (label, value, color) in enumerate(values):
        x = 128 + index * 145
        top = baseline - value * 4
        canvas.rectangle(x, top, x + 82, baseline, color)
        canvas.text(x + 28, top - 26, str(value), 2, color)
        canvas.text(x + 2, 424, label, 2, INK)


def line_chart(canvas: DocumentCanvas) -> None:
    values = (("MON", 120), ("TUE", 150), ("WED", 135), ("THU", 180), ("FRI", 165))
    left, baseline = 92, 404
    canvas.line((left, 112), (left, baseline), INK)
    canvas.line((left, baseline), (704, baseline), INK)
    points: list[tuple[int, int]] = []
    for index, (label, value) in enumerate(values):
        x = 130 + index * 130
        y = baseline - (value - 90) * 3
        points.append((x, y))
        canvas.text(x - 12, 426, label, 2, INK)
        canvas.text(x - 14, y - 30, str(value), 2, BLUE)
    for start, end in zip(points, points[1:]):
        canvas.line(start, end, BLUE, 4)
    for x, y in points:
        canvas.circle(x + 1, y + 1, 7, PAPER)
        canvas.circle(x + 1, y + 1, 4, BLUE)


def project_status(canvas: DocumentCanvas) -> None:
    label_value(canvas, 108, "PROJECT", "ORION", TEAL)
    label_value(canvas, 154, "OWNER", "MAYA CHEN", TEAL)
    label_value(canvas, 200, "BUDGET", "$125000", TEAL)
    label_value(canvas, 246, "SPENT", "$87500", TEAL)
    label_value(canvas, 292, "DEADLINE", "2026-11-30", TEAL)
    canvas.rectangle(52, 358, 700, 422, (236, 253, 245))
    canvas.text(72, 380, "STATUS", 3, GREEN)
    canvas.text(430, 380, "ON TRACK", 3, GREEN)


def energy(canvas: DocumentCanvas) -> None:
    draw_table(
        canvas,
        ("SITE", "SOLAR", "WIND", "TOTAL"),
        (("A", "25", "15", "40"), ("B", "18", "32", "50"), ("C", "30", "20", "50"), ("D", "22", "12", "34")),
        (170, 160, 160, 150),
    )


SCENES: tuple[tuple[str, str, Color, Callable[[DocumentCanvas], None]], ...] = (
    ("receipt-cafe.png", "OAK CAFE", BLUE, receipt),
    ("invoice-studio.png", "INVOICE", PURPLE, invoice),
    ("schedule-lab.png", "LAB SCHEDULE", TEAL, schedule),
    ("inventory-table.png", "INVENTORY", AMBER, inventory),
    ("sales-bar-chart.png", "REGIONAL SALES", BLUE, bar_chart),
    ("traffic-line-chart.png", "DAILY TRAFFIC", BLUE, line_chart),
    ("project-status.png", "PROJECT STATUS", TEAL, project_status),
    ("energy-table.png", "ENERGY OUTPUT", GREEN, energy),
)


def generate(output_dir: Path) -> list[Path]:
    generated: list[Path] = []
    for filename, title, accent, scene in SCENES:
        canvas = base_document(title, accent)
        scene(canvas)
        destination = output_dir / filename
        canvas.write_png(destination)
        generated.append(destination)
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("examples/assets/synthetic-docs-v1"),
    )
    args = parser.parse_args()
    generated = generate(args.output_dir)
    print(f"Generated {len(generated)} images in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

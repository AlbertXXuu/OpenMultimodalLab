"""Build the factual short-video demo from committed formal evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


TASK_ID = "video-right-end"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORMAL_INPUT = PROJECT_ROOT / "runs" / "formal-evaluation-input.jsonl"
VIDEO_PATH = (
    PROJECT_ROOT
    / "examples"
    / "assets"
    / "synthetic-video-v1"
    / "motion-right-red-square.avi"
)
RESULTS = {
    "Qwen3-VL-2B": PROJECT_ROOT
    / "docs"
    / "reports"
    / "results"
    / "2026-08-10-qwen3-vl-v1.0.0-formal.jsonl",
    "SmolVLM2-500M": PROJECT_ROOT
    / "docs"
    / "reports"
    / "results"
    / "2026-08-10-smolvlm2-v1.0.0-formal.jsonl",
}
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "assets" / "video-benchmark-demo.gif"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _task() -> dict[str, Any]:
    matches = [item for item in _load_jsonl(FORMAL_INPUT) if item["id"] == TASK_ID]
    if len(matches) != 1:
        raise ValueError(f"expected one {TASK_ID!r} task, found {len(matches)}")
    task = matches[0]
    if task["media"] != [VIDEO_PATH.relative_to(PROJECT_ROOT).as_posix()]:
        raise ValueError("the demo task no longer references the expected video")
    return task


def _result(path: Path) -> dict[str, Any]:
    matches = [
        item
        for item in _load_jsonl(path)
        if item.get("phase") == "measurement"
        and item.get("repetition") == 1
        and item.get("task_id") == TASK_ID
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one repetition-1 {TASK_ID!r} result in {path.name}"
        )
    result = matches[0]
    if result.get("status") != "success":
        raise ValueError(f"demo source is not successful: {path.name}")
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_demo(output: Path) -> None:
    try:
        import av
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "build_video_demo.py requires the video-model environment "
            "with PyAV and Pillow installed"
        ) from exc

    task = _task()
    results = {name: _result(path) for name, path in RESULTS.items()}
    expected = task["expected_keywords"][0]
    if expected != "right":
        raise ValueError("the expected demo answer changed")
    if results["Qwen3-VL-2B"]["score"] != 1.0:
        raise ValueError("the recorded Qwen demo result is no longer a pass")
    if results["SmolVLM2-500M"]["score"] != 0.0:
        raise ValueError("the recorded SmolVLM2 demo result is no longer a failure")

    with av.open(str(VIDEO_PATH)) as container:
        video_frames = [frame.to_image().convert("RGB") for frame in container.decode(video=0)]
    if len(video_frames) != 16 or video_frames[0].size != (160, 120):
        raise ValueError(
            f"unexpected demo video shape: frames={len(video_frames)}, "
            f"size={video_frames[0].size if video_frames else None}"
        )

    title_font = ImageFont.load_default(size=28)
    heading_font = ImageFont.load_default(size=21)
    body_font = ImageFont.load_default(size=17)
    small_font = ImageFont.load_default(size=14)
    rendered: list[Any] = []
    for index, source in enumerate(video_frames, start=1):
        canvas = Image.new("RGB", (960, 540), "#0d1117")
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (36, 22),
            "Short-video benchmark: where does the red square end?",
            fill="#f0f6fc",
            font=title_font,
        )

        draw.rounded_rectangle(
            (34, 84, 522, 460), radius=16, fill="#161b22", outline="#30363d", width=2
        )
        frame = source.resize((480, 360), Image.Resampling.NEAREST)
        canvas.paste(frame, (38, 88))
        draw.text(
            (38, 472),
            f"Frame {index:02d}/16 - project-generated Apache-2.0 media",
            fill="#8b949e",
            font=small_font,
        )

        draw.rounded_rectangle(
            (550, 84, 926, 504), radius=16, fill="#161b22", outline="#30363d", width=2
        )
        draw.text((578, 112), "Expected answer", fill="#8b949e", font=body_font)
        draw.text((578, 140), "right", fill="#f0f6fc", font=heading_font)

        qwen = results["Qwen3-VL-2B"]
        draw.text((578, 202), "Qwen3-VL-2B", fill="#8b949e", font=body_font)
        draw.text(
            (578, 230),
            f"{qwen['response_text']}  PASS",
            fill="#3fb950",
            font=heading_font,
        )

        smol = results["SmolVLM2-500M"]
        draw.text((578, 292), "SmolVLM2-500M", fill="#8b949e", font=body_font)
        draw.text(
            (578, 320),
            f"{smol['response_text']}  FAIL",
            fill="#f85149",
            font=heading_font,
        )

        draw.line((578, 382, 898, 382), fill="#30363d", width=2)
        draw.text(
            (578, 404),
            "Committed formal run - repetition 1",
            fill="#c9d1d9",
            font=body_font,
        )
        draw.text(
            (578, 438),
            "One warm-up + three measured grids",
            fill="#8b949e",
            font=small_font,
        )
        draw.text(
            (578, 466),
            "No model was rerun to build this GIF",
            fill="#8b949e",
            font=small_font,
        )
        rendered.append(
            canvas.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    rendered[0].save(
        output,
        save_all=True,
        append_images=rendered[1:],
        duration=125,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"Wrote {len(rendered)} frames to {output}")
    print(f"Artifact SHA-256: {_sha256(output)}")
    for name, path in RESULTS.items():
        print(f"{name} source SHA-256: {_sha256(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_demo(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

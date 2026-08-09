from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TUTORIAL = PROJECT_ROOT / "docs" / "tutorials" / "video-benchmark.md"
DEMO = PROJECT_ROOT / "docs" / "assets" / "video-benchmark-demo.gif"
GENERATOR = PROJECT_ROOT / "scripts" / "build_video_demo.py"


class VideoDemoTests(unittest.TestCase):
    def test_demo_artifact_and_rebuild_path_are_committed(self) -> None:
        self.assertTrue(GENERATOR.is_file())
        self.assertTrue(TUTORIAL.is_file())
        self.assertTrue(DEMO.is_file())
        data = DEMO.read_bytes()
        self.assertTrue(data.startswith((b"GIF87a", b"GIF89a")))
        self.assertGreater(len(data), 10_000)
        self.assertLess(len(data), 4 * 1024 * 1024)

    def test_tutorial_discloses_the_preserved_pass_and_failure(self) -> None:
        text = TUTORIAL.read_text(encoding="utf-8")
        for marker in (
            "synthetic-video-v1",
            "video-right-end",
            "Qwen3-VL-2B answered `right` and passed",
            "SmolVLM2-500M",
            "answered `left.` and failed",
            "scripts/build_video_demo.py",
            "--warmup 1",
            "--repetitions 3",
            "--media-root .",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()

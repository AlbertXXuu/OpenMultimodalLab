from __future__ import annotations

import struct
import unittest
from pathlib import Path


class SocialPreviewTests(unittest.TestCase):
    def test_committed_social_preview_matches_github_dimensions(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        preview = project_root / "docs/assets/alvenx-social-preview.png"
        payload = preview.read_bytes()

        self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", payload[16:24])
        self.assertEqual((width, height), (1280, 640))
        self.assertLess(len(payload), 1_000_000)

    def test_social_preview_has_a_reproducible_builder(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        builder = (
            project_root / "scripts/build_social_preview.py"
        ).read_text(encoding="utf-8")

        self.assertIn("InstrumentSans-wdth-wght.woff2.b64", builder)
        self.assertIn("#4f8cff", builder)
        self.assertIn("#2563eb", builder)
        self.assertIn("#1e3a8a", builder)
        self.assertIn('class="brand-l"', builder)
        self.assertIn("margin-right: .014em", builder)
        self.assertIn('class="brand-x"', builder)
        self.assertIn("margin-left: -.079em", builder)
        self.assertIn("font-stretch: 98%", builder)
        self.assertIn("letter-spacing: -.036em", builder)
        self.assertIn("justify-items: center", builder)
        self.assertIn("transform: translateX(2.5px)", builder)
        self.assertIn(">MULTIMODAL EVIDENCE</div>", builder)
        self.assertNotIn("#22c55e", builder.casefold())


if __name__ == "__main__":
    unittest.main()

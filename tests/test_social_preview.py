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
        self.assertIn("LOCKUP_PATH", builder)
        self.assertIn("base64.b64encode(LOCKUP_PATH.read_bytes())", builder)
        self.assertIn("data:image/svg+xml;base64,{wordmark_base64}", builder)
        self.assertNotIn('class="brand-l"', builder)
        self.assertNotIn('class="brand-x"', builder)
        self.assertNotIn("#22c55e", builder.casefold())


if __name__ == "__main__":
    unittest.main()

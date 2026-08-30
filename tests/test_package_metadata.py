from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from openmultimodal_lab import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def test_candidate_version_matches_closure_version(self) -> None:
        pyproject = tomllib.loads(
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(__version__, "1.1.1")
        self.assertEqual(pyproject["project"]["version"], __version__)
        self.assertIn(
            "Development Status :: 4 - Beta",
            pyproject["project"]["classifiers"],
        )

    def test_public_attribution_uses_the_owner_approved_identity(self) -> None:
        pyproject = tomllib.loads(
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        notice = (PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")
        citation = (PROJECT_ROOT / "CITATION.cff").read_text(encoding="utf-8")
        trademarks = (PROJECT_ROOT / "TRADEMARKS.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(
            pyproject["project"]["authors"],
            [{"name": "AlbertXXuu"}],
        )
        self.assertIn("Copyright 2026 AlbertXXuu", notice)
        self.assertIn("- name: AlbertXXuu", citation)
        self.assertNotIn("alias:", citation)
        self.assertIn("`ALONICA` is a developer ID", trademarks)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from openmultimodal_lab import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def test_candidate_version_matches_owner_approved_public_version(self) -> None:
        pyproject = tomllib.loads(
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(__version__, "1.0.0")
        self.assertEqual(pyproject["project"]["version"], __version__)
        self.assertIn(
            "Development Status :: 4 - Beta",
            pyproject["project"]["classifiers"],
        )


if __name__ == "__main__":
    unittest.main()

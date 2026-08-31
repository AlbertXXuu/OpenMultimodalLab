from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from openmultimodal_lab import __version__
from openmultimodal_lab.studio_assets import BRAND_HEADER_HTML


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_SOFTWARE_VERSION = "1.1.2"


class PackageMetadataTests(unittest.TestCase):
    def test_current_version_matches_maintenance_patch(self) -> None:
        pyproject = tomllib.loads(
            (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

        self.assertEqual(__version__, CURRENT_SOFTWARE_VERSION)
        self.assertEqual(pyproject["project"]["version"], __version__)
        self.assertIn(
            "Development Status :: 4 - Beta",
            pyproject["project"]["classifiers"],
        )

    def test_current_software_version_surfaces_agree(self) -> None:
        tagged_version = f"v{CURRENT_SOFTWARE_VERSION}"
        expected_markers = {
            "README.md": (
                f"current software is the `{tagged_version}` maintenance patch",
                f"git clone --branch {tagged_version} --depth 1",
            ),
            "README.zh-CN.md": (
                f"当前软件是 `{tagged_version}` 维护修补版",
                f"git clone --branch {tagged_version} --depth 1",
            ),
            "CHANGELOG.md": (
                f"## [{CURRENT_SOFTWARE_VERSION}] - 2026-08-31",
                f"compare/v1.1.1...{tagged_version}",
            ),
            "docs/MAINTENANCE.md": (
                f"Current public and maintained release: `{tagged_version}`",
            ),
            "TASKS.md": (f"当前公开维护软件是 `{tagged_version}`",),
            "docs/reports/v1.1.2-patch-validation.md": (
                f"# OpenMultimodalLab {tagged_version} patch validation",
                "Status: **VALIDATED RELEASE SOURCE**",
            ),
        }

        for relative_path, markers in expected_markers.items():
            text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
            for marker in markers:
                with self.subTest(path=relative_path, marker=marker):
                    self.assertIn(marker, text)

        self.assertIn(
            f"Studio {tagged_version} · Evidence v1.0.0",
            BRAND_HEADER_HTML,
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

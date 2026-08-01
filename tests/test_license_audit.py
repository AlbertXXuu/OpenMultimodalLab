from __future__ import annotations

import json
import sys
import unittest
from email.message import Message
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from audit_runtime_licenses import (  # noqa: E402
    analyze_binary_names,
    audit_packages,
    canonicalize_name,
    classify_license,
    resolve_declared_license,
    validate_policy,
)


POLICY_PATH = PROJECT_ROOT / "docs" / "license-audit-policy.json"


class LicenseAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_committed_policy_is_complete_and_unambiguous(self) -> None:
        self.assertEqual(validate_policy(self.policy), [])
        declared_values = [
            value
            for rule in self.policy["license_rules"]
            for value in rule["declared_values"]
        ]
        self.assertEqual(len(declared_values), len(set(declared_values)))
        self.assertFalse(self.policy["ffmpeg"]["bundled_runtime_allowed"])
        self.assertGreaterEqual(len(self.policy["models"]), 2)
        invalid = json.loads(json.dumps(self.policy))
        invalid["ffmpeg"]["gpl_binary_markers"] = [1]
        self.assertTrue(validate_policy(invalid))

    def test_name_and_license_resolution_are_deterministic(self) -> None:
        self.assertEqual(canonicalize_name("HuggingFace_Hub"), "huggingface-hub")
        message = Message()
        message["License-Expression"] = "BSD-3-Clause"
        message["License"] = "legacy value"
        message["Classifier"] = "License :: OSI Approved :: MIT License"
        self.assertEqual(resolve_declared_license(message), "BSD-3-Clause")
        self.assertEqual(
            classify_license("BSD-3-Clause", self.policy["license_rules"]),
            ("BSD-family", "permissive"),
        )
        self.assertEqual(
            classify_license("unreviewed", self.policy["license_rules"]),
            (None, None),
        )

    def test_package_audit_rejects_license_and_version_drift(self) -> None:
        policy = {
            "license_rules": self.policy["license_rules"],
            "allowed_package_license_tiers": ["permissive"],
            "required_packages": {"demo": "1.0"},
        }
        packages = [
            {
                "name": "demo",
                "versions": ["2.0"],
                "declared_licenses": ["unknown-license"],
            }
        ]

        findings = audit_packages(packages, policy)

        self.assertTrue(any("unreviewed license" in item for item in findings))
        self.assertTrue(any("do not match 1.0" in item for item in findings))

    def test_ffmpeg_binary_markers_expose_copyleft_and_nonfree_risk(self) -> None:
        evidence = analyze_binary_names(
            [
                "avcodec-62.dll",
                "libx264-165.dll",
                "libx265.dll",
                "libopencore-amrnb.dll",
                "libopencore-amrwb.dll",
                "libfdk-aac.dll",
            ],
            self.policy["ffmpeg"],
        )

        self.assertEqual(
            evidence["gpl_markers_found"],
            ["libx264", "libx265"],
        )
        self.assertEqual(
            evidence["version3_markers_found"],
            ["libopencore-amrnb", "libopencore-amrwb"],
        )
        self.assertEqual(evidence["nonfree_markers_found"], ["libfdk"])
        self.assertEqual(
            evidence["effective_ffmpeg_license"],
            "GPL-3.0-or-later",
        )


if __name__ == "__main__":
    unittest.main()

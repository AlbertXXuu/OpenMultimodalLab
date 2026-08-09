from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_release_readiness import (
    PERFORMANCE_FIELDS,
    _constraints_status,
    _formal_result_status,
    _license_report_status,
    _license_snapshot_status,
    audit_release_readiness,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKER = PROJECT_ROOT / "scripts" / "check_release_readiness.py"


class ReleaseReadinessTests(unittest.TestCase):
    @staticmethod
    def _formal_records(*, omit_task: bool = False) -> list[dict[str, object]]:
        usage = {field: 1.0 for field in PERFORMANCE_FIELDS}
        records: list[dict[str, object]] = [
            {
                "phase": "warmup",
                "repetition": 1,
                "task_id": "task-a",
                "status": "success",
                "usage": usage,
            }
        ]
        for repetition in (1, 2, 3):
            records.append(
                {
                    "phase": "measurement",
                    "repetition": repetition,
                    "task_id": "task-a",
                    "status": "success",
                    "usage": {**usage, "model_load_ms": 0.0},
                }
            )
            if not (omit_task and repetition == 3):
                records.append(
                    {
                        "phase": "measurement",
                        "repetition": repetition,
                        "task_id": "task-b",
                        "status": "invalid_input",
                        "error": "bounded decoder rejected input",
                        "usage": {},
                    }
                )
        return records

    def test_formal_protocol_preserves_disclosed_failures(self) -> None:
        passed, detail = _formal_result_status(self._formal_records())

        self.assertTrue(passed)
        self.assertIn("failures=3", detail)
        self.assertIn("complete_grid=True", detail)

    def test_formal_protocol_rejects_incomplete_repeat_grid(self) -> None:
        passed, detail = _formal_result_status(
            self._formal_records(omit_task=True)
        )

        self.assertFalse(passed)
        self.assertIn("complete_grid=False", detail)

    def test_license_snapshot_requires_integrity_and_clean_evidence(self) -> None:
        value = {
            "schema_version": "1.0",
            "status": "PASS",
            "distribution_scope": "source-only-no-runtime-binaries",
            "repository": {
                "commit": "a" * 40,
                "dirty": False,
                "forbidden_runtime_files": [],
            },
            "packages": [
                {
                    "name": "av",
                    "versions": ["18.0.0"],
                    "declared_licenses": ["BSD-3-Clause"],
                    "license_classifications": [
                        {
                            "declared": "BSD-3-Clause",
                            "normalized": "BSD-family",
                            "tier": "permissive",
                        }
                    ],
                }
            ],
            "models": [
                {
                    "model_id": "model-a",
                    "revision": "b" * 40,
                    "license": "Apache-2.0",
                },
                {
                    "model_id": "model-b",
                    "revision": "c" * 40,
                    "license": "Apache-2.0",
                },
            ],
            "ffmpeg": {
                "gpl_markers_found": ["libx264", "libx265"],
                "version3_markers_found": [
                    "libopencore-amrnb",
                    "libopencore-amrwb",
                ],
                "nonfree_markers_found": [],
                "effective_ffmpeg_license": "GPL-3.0-or-later",
                "bundled_runtime_allowed": False,
                "bundled_binaries": [
                    {
                        "name": "avcodec.dll",
                        "size_bytes": 100,
                        "sha256": "d" * 64,
                    }
                ],
            },
            "findings": [],
            "warnings": ["source-only distribution"],
        }
        value["snapshot_sha256"] = hashlib.sha256(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "snapshot.json"
            snapshot.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )
            constraints = Path(temp_dir) / "constraints.txt"
            constraints.write_text("av==18.0.0\n", encoding="utf-8")
            report = Path(temp_dir) / "report.md"
            report.write_text(
                "# Final dependency and license audit\n\n"
                "Outcome: PASS\n\n"
                "Reviewer: Test Reviewer\n\n"
                "Review date: 2026-08-02\n\n"
                f"Snapshot SHA-256: `{value['snapshot_sha256']}`\n",
                encoding="utf-8",
            )
            passed, detail = _license_snapshot_status(snapshot)
            constraints_passed, _ = _constraints_status(
                constraints,
                snapshot,
            )
            report_passed, _ = _license_report_status(report, snapshot)
            value["repository"]["dirty"] = True
            snapshot.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )
            tampered, _ = _license_snapshot_status(snapshot)

        self.assertTrue(passed)
        self.assertTrue(constraints_passed)
        self.assertTrue(report_passed)
        self.assertIn("hash_match=True", detail)
        self.assertFalse(tampered)

    def test_current_readiness_reports_proven_gates_and_real_blockers(self) -> None:
        checks = {
            check.id: check
            for check in audit_release_readiness(PROJECT_ROOT)
        }

        for check_id in (
            "TASK-PROVENANCE",
            "TASK-COUNT",
            "HUMAN-REVIEW",
            "TWO-REAL-MODELS",
            "FORMAL-IMAGE",
            "FORMAL-DOCUMENT",
            "FORMAL-PROTOCOL",
            "DOCUMENTATION",
            "REPORT-BUNDLE-TOOLING",
            "VIDEO-TASKS",
            "LINUX-CI-CONTRACT",
        ):
            with self.subTest(check_id=check_id):
                self.assertTrue(checks[check_id].passed)

        for check_id in (
            "FORMAL-VIDEO",
            "VIDEO-DEMO",
            "FINAL-LICENSE-AUDIT",
            "FINAL-FRESH-WINDOWS",
            "FINAL-LINUX-CI",
            "OWNER-PUBLICATION-APPROVAL",
            "FINAL-CANDIDATE-VALIDATION",
        ):
            with self.subTest(check_id=check_id):
                self.assertFalse(checks[check_id].passed)

        self.assertTrue(checks["OWNER-NAMING-APPROVAL"].passed)
        self.assertIn("import", checks["OWNER-NAMING-APPROVAL"].evidence)

    def test_owner_naming_approval_matches_recorded_decision(self) -> None:
        approvals = json.loads(
            (PROJECT_ROOT / "docs/release-approvals.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(approvals["project_name"], "OpenMultimodalLab")
        self.assertEqual(approvals["package_name"], "openmultimodal-lab")
        self.assertEqual(approvals["import_module"], "openmultimodal_lab")
        self.assertEqual(approvals["cli_name"], "oml")
        self.assertEqual(
            approvals["video_dataset_name"], "synthetic-video-v1"
        )
        self.assertEqual(
            approvals["robustness_dataset_name"],
            "synthetic-robustness-v1",
        )
        self.assertEqual(approvals["public_version"], "v1.0.0")
        self.assertFalse(approvals["make_repository_public"])
        self.assertFalse(approvals["formal_release_authorized"])

    def test_final_candidate_corpus_has_valid_owner_review(self) -> None:
        checks = {
            check.id: check
            for check in audit_release_readiness(PROJECT_ROOT)
        }

        self.assertTrue(checks["TASK-COUNT"].passed)
        self.assertIn("102 unique", checks["TASK-COUNT"].evidence)
        self.assertTrue(checks["VIDEO-TASKS"].passed)
        self.assertIn("24 canonical", checks["VIDEO-TASKS"].evidence)
        self.assertTrue(checks["HUMAN-REVIEW"].passed)
        self.assertIn(
            "the corpus has 102 tasks",
            checks["HUMAN-REVIEW"].evidence,
        )

    def test_strict_mode_fails_while_release_requirements_are_open(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(CHECKER), "--strict"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("Ready: no", completed.stdout)
        self.assertIn("[PASS] TASK-COUNT", completed.stdout)
        self.assertIn("[PASS] HUMAN-REVIEW", completed.stdout)
        self.assertIn("[OPEN] OWNER-PUBLICATION-APPROVAL", completed.stdout)


if __name__ == "__main__":
    unittest.main()

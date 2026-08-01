from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from scripts.check_release_readiness import (
    PERFORMANCE_FIELDS,
    _formal_result_status,
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

    def test_current_readiness_reports_proven_gates_and_real_blockers(self) -> None:
        checks = {
            check.id: check
            for check in audit_release_readiness(PROJECT_ROOT)
        }

        for check_id in (
            "TASK-PROVENANCE",
            "TWO-REAL-MODELS",
            "FORMAL-IMAGE",
            "FORMAL-DOCUMENT",
            "FORMAL-PROTOCOL",
            "DOCUMENTATION",
            "LINUX-CI-CONTRACT",
        ):
            with self.subTest(check_id=check_id):
                self.assertTrue(checks[check_id].passed)

        for check_id in (
            "TASK-COUNT",
            "HUMAN-REVIEW",
            "VIDEO-TASKS",
            "FORMAL-VIDEO",
            "VIDEO-DEMO",
            "FINAL-LICENSE-AUDIT",
            "FINAL-FRESH-WINDOWS",
            "FINAL-LINUX-CI",
            "OWNER-NAMING-APPROVAL",
            "OWNER-PUBLICATION-APPROVAL",
            "FINAL-CANDIDATE-VALIDATION",
        ):
            with self.subTest(check_id=check_id):
                self.assertFalse(checks[check_id].passed)

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
        self.assertIn("[OPEN] TASK-COUNT", completed.stdout)
        self.assertIn("[OPEN] OWNER-PUBLICATION-APPROVAL", completed.stdout)


if __name__ == "__main__":
    unittest.main()

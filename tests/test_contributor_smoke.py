from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "contributor_smoke.py"


class ContributorSmokeTests(unittest.TestCase):
    def test_installed_core_workflow_passes_offline(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["records"], 3)
        self.assertEqual(result["successful_records"], 3)
        self.assertLess(result["elapsed_seconds"], 60)
        self.assertIn("socket guard enforced", result["network_policy"])
        self.assertEqual(
            result["artifacts_validated"],
            ["smoke.jsonl", "smoke.jsonl.manifest.json"],
        )


if __name__ == "__main__":
    unittest.main()

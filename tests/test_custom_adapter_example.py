from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CustomAdapterExampleTests(unittest.TestCase):
    def run_module(
        self,
        module: str,
        *args: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", module, *args],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_example_runs_through_real_runner(self) -> None:
        completed = self.run_module("examples.custom_adapter.run_example")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual(output["status"], "success")
        self.assertEqual(output["backend"], "third-party-fake")
        self.assertTrue(
            output["model_revision"].startswith("fake-backend@sha256:")
        )
        self.assertTrue(output["usage"]["deterministic"])

    def test_copyable_contract_suite_passes(self) -> None:
        completed = self.run_module(
            "unittest",
            "examples.custom_adapter.test_contract",
            "-v",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Ran 5 tests", completed.stderr)


if __name__ == "__main__":
    unittest.main()

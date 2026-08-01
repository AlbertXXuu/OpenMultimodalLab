from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = PROJECT_ROOT / "scripts" / "generate_comparison_chart.py"
COMMITTED_CHART = PROJECT_ROOT / "docs" / "assets" / "model-comparison.svg"


class ResultVisualTests(unittest.TestCase):
    def test_committed_chart_matches_preserved_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            generated = Path(temp_dir) / "model-comparison.svg"
            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--output",
                    str(generated),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            generated_bytes = generated.read_bytes()

        self.assertEqual(COMMITTED_CHART.read_bytes(), generated_bytes)

    def test_chart_contains_values_and_visible_limits(self) -> None:
        chart = COMMITTED_CHART.read_text(encoding="utf-8")

        for expected in (
            "1.000",
            "0.733",
            "183 ms",
            "387 ms",
            "4,093 MiB",
            "1,265 MiB",
            "30/30 successful measurements each",
            "NOT A UNIVERSAL RANKING",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, chart)


if __name__ == "__main__":
    unittest.main()

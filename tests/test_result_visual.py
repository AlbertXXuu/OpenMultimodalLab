from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = PROJECT_ROOT / "scripts" / "generate_comparison_chart.py"
COMMITTED_CHART = PROJECT_ROOT / "docs" / "assets" / "model-comparison.svg"
DOCUMENT_CHART = PROJECT_ROOT / "docs" / "assets" / "document-comparison.svg"
DOCUMENT_QWEN_RESULT = (
    PROJECT_ROOT
    / "docs"
    / "reports"
    / "results"
    / "2026-08-02-qwen3-vl-docs-formal.jsonl"
)
DOCUMENT_SMOL_RESULT = (
    PROJECT_ROOT
    / "docs"
    / "reports"
    / "results"
    / "2026-08-02-smolvlm2-500m-docs-formal.jsonl"
)


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

    def test_document_chart_matches_preserved_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            generated = Path(temp_dir) / "document-comparison.svg"
            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--qwen-result",
                    str(DOCUMENT_QWEN_RESULT),
                    "--smol-result",
                    str(DOCUMENT_SMOL_RESULT),
                    "--output",
                    str(generated),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            generated_bytes = generated.read_bytes()

        self.assertEqual(DOCUMENT_CHART.read_bytes(), generated_bytes)

    def test_document_chart_contains_result_and_protocol_values(self) -> None:
        chart = DOCUMENT_CHART.read_text(encoding="utf-8")

        for expected in (
            "0.719",
            "0.625",
            "353 ms",
            "565 ms",
            "4,180 MiB",
            "1,265 MiB",
            "32 generated tasks",
            "96/96 successful measurements each",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, chart)


if __name__ == "__main__":
    unittest.main()

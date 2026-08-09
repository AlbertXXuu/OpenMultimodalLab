from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from openmultimodal_lab.report_bundle import (
    BUNDLE_FILENAMES,
    build_report_bundle,
    load_comparable_sources,
    verify_report_bundle,
    write_report_bundle,
)
from openmultimodal_lab.reporting import ReportError, validate_formal_run


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "docs" / "reports" / "results"
FORMAL_RESULTS = (
    RESULTS_ROOT / "2026-07-31-qwen3-vl-comparison-formal.jsonl",
    RESULTS_ROOT / "2026-07-31-smolvlm2-500m-comparison-formal.jsonl",
    RESULTS_ROOT / "2026-08-02-qwen3-vl-docs-formal.jsonl",
    RESULTS_ROOT / "2026-08-02-smolvlm2-500m-docs-formal.jsonl",
)
FINAL_RESULTS = (
    RESULTS_ROOT / "2026-08-10-qwen3-vl-v1.0.0-formal.jsonl",
    RESULTS_ROOT / "2026-08-10-smolvlm2-v1.0.0-formal.jsonl",
)
GENERATOR = PROJECT_ROOT / "scripts" / "build_benchmark_report.py"
COMMITTED_BUNDLE = PROJECT_ROOT / "docs" / "reports" / "rebuilt-baseline"
FINAL_BUNDLE = PROJECT_ROOT / "docs" / "reports" / "v1.0.0-candidate"
FINAL_INPUT_SHA256 = (
    "d18e6dce941cfac1fee0d637449229d786d7d6b601c063c0af2266b7e2d7a5a8"
)


class FormalProtocolValidationTests(unittest.TestCase):
    @staticmethod
    def _record(phase: str, repetition: int, task_id: str) -> dict[str, object]:
        return {
            "phase": phase,
            "repetition": repetition,
            "task_id": task_id,
            "status": "success",
            "latency_ms": 25,
            "score": 1,
            "usage": {
                "model_load_ms": 100 if phase == "warmup" else 0,
                "preprocessing_ms": 2,
                "ttft_ms": 5,
                "generation_ms": 20,
                "output_tokens_per_second": 30,
                "peak_gpu_memory_mb": 1000,
            },
        }

    def _formal_records(self) -> list[dict[str, object]]:
        return [
            self._record("warmup", 1, "task-1"),
            *[
                self._record("measurement", repetition, task_id)
                for repetition in (1, 2, 3)
                for task_id in ("task-1", "task-2")
            ],
        ]

    def test_exact_three_repeat_grid_passes(self) -> None:
        validation = validate_formal_run(self._formal_records())

        self.assertTrue(validation.passed)
        self.assertEqual(validation.repetitions, (1, 2, 3))
        self.assertTrue(validation.complete_repeat_grid)

    def test_fourth_repetition_is_not_formal(self) -> None:
        records = self._formal_records()
        records.extend(
            self._record("measurement", 4, task_id)
            for task_id in ("task-1", "task-2")
        )

        validation = validate_formal_run(records)

        self.assertFalse(validation.passed)
        self.assertIn("exactly 1, 2, and 3", " ".join(validation.issues))

    def test_incomplete_repeat_grid_is_not_formal(self) -> None:
        records = self._formal_records()
        records.pop()

        validation = validate_formal_run(records)

        self.assertFalse(validation.passed)
        self.assertFalse(validation.complete_repeat_grid)


class ReportBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = load_comparable_sources(
            FORMAL_RESULTS,
            project_root=PROJECT_ROOT,
        )

    def test_bundle_is_complete_deterministic_and_portable(self) -> None:
        first = build_report_bundle(
            self.sources,
            project_root=PROJECT_ROOT,
        )
        second = build_report_bundle(
            tuple(reversed(self.sources)),
            project_root=PROJECT_ROOT,
        )

        self.assertEqual(set(first), set(BUNDLE_FILENAMES))
        self.assertEqual(first, second)
        combined = b"\n".join(first.values()).decode("utf-8")
        self.assertNotRegex(combined, r"(?i)(?<![a-z0-9])[a-z]:[\\/]")
        self.assertNotRegex(combined, r"(?i)/(?:home|users)/[^/\s]+/")

    def test_bundle_contains_expected_metrics_and_valid_svg(self) -> None:
        bundle = build_report_bundle(
            self.sources,
            project_root=PROJECT_ROOT,
        )
        rows = list(
            csv.DictReader(
                io.StringIO(bundle["run-summary.csv"].decode("utf-8"))
            )
        )

        self.assertEqual(len(rows), 4)
        qwen_docs = next(
            row
            for row in rows
            if row["dataset_versions"] == "synthetic-docs-v1"
            and row["backend"] == "qwen3-vl"
        )
        self.assertEqual(qwen_docs["unique_tasks"], "32")
        self.assertEqual(qwen_docs["measurement_attempts"], "96")
        self.assertEqual(qwen_docs["mean_score"], "0.718750")
        self.assertEqual(qwen_docs["failed_measurements"], "0")
        self.assertEqual(
            bundle["failures.csv"].decode("utf-8").count("\n"),
            1,
        )
        ElementTree.fromstring(bundle["overview.svg"])
        report = bundle["report.md"].decode("utf-8")
        self.assertIn("exactly one successful warm-up", report)
        self.assertIn("not a universal model ranking", report)

    def test_committed_baseline_matches_verified_sources_byte_for_byte(
        self,
    ) -> None:
        generated = build_report_bundle(
            self.sources,
            project_root=PROJECT_ROOT,
        )

        for name, content in generated.items():
            with self.subTest(name=name):
                self.assertEqual((COMMITTED_BUNDLE / name).read_bytes(), content)
        manifest = verify_report_bundle(
            COMMITTED_BUNDLE,
            project_root=PROJECT_ROOT,
        )
        self.assertEqual(manifest["status"], "verified-formal-sources")

    def test_final_102_task_bundle_is_complete_and_byte_exact(self) -> None:
        sources = load_comparable_sources(
            FINAL_RESULTS,
            project_root=PROJECT_ROOT,
        )
        self.assertEqual(
            {source.backend for source in sources},
            {"qwen3-vl", "smolvlm2"},
        )
        self.assertEqual({len(source.task_ids) for source in sources}, {102})
        self.assertEqual(
            {source.dataset_sha256 for source in sources},
            {FINAL_INPUT_SHA256},
        )
        generated = build_report_bundle(sources, project_root=PROJECT_ROOT)
        for name, content in generated.items():
            with self.subTest(name=name):
                self.assertEqual((FINAL_BUNDLE / name).read_bytes(), content)

        manifest = verify_report_bundle(FINAL_BUNDLE, project_root=PROJECT_ROOT)
        self.assertEqual(len(manifest["sources"]), 2)
        self.assertEqual(len(manifest["outputs"]), 5)
        report = generated["report.md"].decode("utf-8")
        self.assertIn("102 unique dataset tasks", report)
        self.assertIn("4 retained dataset versions", report)

    def test_written_bundle_verifies_and_detects_tampering(self) -> None:
        bundle = build_report_bundle(
            self.sources,
            project_root=PROJECT_ROOT,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            write_report_bundle(output, bundle)
            manifest = verify_report_bundle(
                output,
                project_root=PROJECT_ROOT,
            )
            self.assertEqual(len(manifest["sources"]), 4)
            self.assertEqual(len(manifest["outputs"]), 5)

            (output / "report.md").write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ReportError, "mismatch"):
                verify_report_bundle(output, project_root=PROJECT_ROOT)

    def test_failed_measurement_is_preserved_and_path_redacted(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            copied_results: list[Path] = []
            for index, original in enumerate(FORMAL_RESULTS[:2]):
                records = [
                    json.loads(line)
                    for line in original.read_text(encoding="utf-8").splitlines()
                ]
                if index == 0:
                    failed = next(
                        record
                        for record in records
                        if record.get("phase") == "measurement"
                    )
                    failed["status"] = "generation_error"
                    failed["score"] = None
                    private_path = "D:" + r"\private\clip.avi"
                    failed["error"] = f"decoder failed at {private_path}"
                result = Path(temp_dir) / f"formal-{index}.jsonl"
                result_bytes = (
                    "\n".join(
                        json.dumps(record, ensure_ascii=False)
                        for record in records
                    )
                    + "\n"
                ).encode("utf-8")
                result.write_bytes(result_bytes)

                original_manifest = original.with_suffix(".manifest.json")
                manifest = json.loads(
                    original_manifest.read_text(encoding="utf-8")
                )
                manifest["retry_records"] = 0
                manifest["protocol"]["max_retries"] = 0
                manifest["output"] = {
                    "path": result.relative_to(PROJECT_ROOT).as_posix(),
                    "sha256": hashlib.sha256(result_bytes).hexdigest(),
                    "size_bytes": len(result_bytes),
                }
                result.with_suffix(".manifest.json").write_text(
                    json.dumps(manifest, indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                copied_results.append(result)

            sources = load_comparable_sources(
                copied_results,
                project_root=PROJECT_ROOT,
            )
            bundle = build_report_bundle(sources, project_root=PROJECT_ROOT)

        failures = list(
            csv.DictReader(io.StringIO(bundle["failures.csv"].decode("utf-8")))
        )
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["status"], "generation_error")
        self.assertIn("<local-path>", failures[0]["error"])
        self.assertNotIn("D:" + r"\private", failures[0]["error"])

    def test_script_builds_and_verifies_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "bundle"
            build_command = [
                sys.executable,
                str(GENERATOR),
                *[
                    argument
                    for result in FORMAL_RESULTS
                    for argument in ("--input", str(result))
                ],
                "--output-dir",
                str(output),
            ]
            built = subprocess.run(
                build_command,
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            verified = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--verify",
                    "--output-dir",
                    str(output),
                ],
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertRegex(verified.stdout, re.compile(r"4 sources, 5 outputs"))


if __name__ == "__main__":
    unittest.main()

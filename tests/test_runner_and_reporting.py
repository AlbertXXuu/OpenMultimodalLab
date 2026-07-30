from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openmultimodal_lab.adapters import MockAdapter
from openmultimodal_lab.adapters.errors import AdapterOutOfMemoryError
from openmultimodal_lab.models import EvaluationTask, ScoringConfig
from openmultimodal_lab.reporting import load_records, summarize
from openmultimodal_lab.runner import run_benchmark


class RunnerAndReportingTests(unittest.TestCase):
    def test_end_to_end_mock_run(self) -> None:
        tasks = [
            EvaluationTask(
                id="task-1",
                prompt="Describe it.",
                expected_keywords=("red circle", "blue square"),
                metadata={"category": "image-description"},
            ),
            EvaluationTask(id="task-2", prompt="Unscored task."),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark(tasks, MockAdapter(), output)
            loaded = load_records(output)
            summary = summarize(loaded)

        self.assertEqual(len(records), 2)
        self.assertEqual(summary["total_tasks"], 2)
        self.assertEqual(summary["successful_tasks"], 2)
        self.assertEqual(summary["scored_tasks"], 1)
        self.assertEqual(summary["mean_score"], 1.0)
        self.assertTrue(all(record.status == "success" for record in records))
        self.assertTrue(all(record.schema_version == "0.2" for record in records))
        self.assertEqual(records[0].metric_name, "keyword_coverage")
        self.assertEqual(records[0].task_schema_version, "1.1")

    def test_adapter_failure_is_recorded(self) -> None:
        class FailingAdapter:
            name = "failing"

            def generate(self, task: EvaluationTask):
                raise RuntimeError("injected failure")

        task = EvaluationTask(id="failure", prompt="Fail safely.")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark([task], FailingAdapter(), output)

        self.assertEqual(records[0].status, "generation_error")
        self.assertIn("injected failure", records[0].error or "")

    def test_typed_adapter_failure_keeps_specific_status(self) -> None:
        class OutOfMemoryAdapter:
            name = "memory-limited"
            revision = "revision-1"

            def generate(self, task: EvaluationTask):
                raise AdapterOutOfMemoryError("CUDA out of memory")

        task = EvaluationTask(id="failure", prompt="Fail specifically.")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark([task], OutOfMemoryAdapter(), output)

        self.assertEqual(records[0].status, "out_of_memory")
        self.assertEqual(records[0].model_revision, "revision-1")

    def test_evaluation_failure_preserves_generated_response(self) -> None:
        task = EvaluationTask(
            id="invalid-programmatic-scorer",
            prompt="Generate successfully.",
            expected_keywords=("answer",),
            scoring=ScoringConfig(type="not-registered"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark([task], MockAdapter(), output)

        self.assertEqual(records[0].status, "evaluation_error")
        self.assertIn("Mock observation", records[0].response_text or "")
        self.assertIn("unsupported scoring type", records[0].error or "")


if __name__ == "__main__":
    unittest.main()

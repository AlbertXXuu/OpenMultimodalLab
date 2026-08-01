from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openmultimodal_lab.adapters import MockAdapter
from openmultimodal_lab.adapters.errors import (
    AdapterOutOfMemoryError,
    AdapterTimeoutError,
)
from openmultimodal_lab.models import (
    EvaluationTask,
    ModelOutput,
    ScoringConfig,
)
from openmultimodal_lab.reporting import ReportError, load_records, summarize
from openmultimodal_lab.runner import ResumeError, run_benchmark


class RunnerAndReportingTests(unittest.TestCase):
    def test_report_rejects_oversized_or_non_utf8_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            oversized = root / "oversized.jsonl"
            oversized.write_bytes(b"{\"value\": 1}\n")
            with patch(
                "openmultimodal_lab.reporting.MAX_RESULT_LINE_BYTES",
                5,
            ), self.assertRaisesRegex(ReportError, "line safety limit"):
                load_records(oversized)

            invalid = root / "invalid.jsonl"
            invalid.write_bytes(b"\xff\n")
            with self.assertRaisesRegex(ReportError, "not valid UTF-8"):
                load_records(invalid)

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
        self.assertTrue(all(record.schema_version == "0.4" for record in records))
        self.assertTrue(all(record.phase == "measurement" for record in records))
        self.assertTrue(all(record.repetition == 1 for record in records))
        self.assertEqual(records[0].metric_name, "keyword_coverage")
        self.assertEqual(records[0].task_schema_version, "1.2")

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

    def test_retryable_failure_is_durable_before_success(self) -> None:
        class FlakyAdapter:
            name = "flaky"
            revision = "revision-1"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: EvaluationTask) -> ModelOutput:
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("transient failure")
                return ModelOutput(
                    text="answer",
                    backend=self.name,
                    model_revision=self.revision,
                )

        task = EvaluationTask(
            id="retry",
            prompt="Retry safely.",
            expected_keywords=("answer",),
        )
        checkpoints: list[int] = []
        adapter = FlakyAdapter()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark(
                [task],
                adapter,
                output,
                max_retries=1,
                on_record_persisted=lambda current: checkpoints.append(
                    len(current)
                ),
            )
            loaded = load_records(output)
            summary = summarize(loaded)

        self.assertEqual(adapter.calls, 2)
        self.assertEqual(checkpoints, [1, 2])
        self.assertEqual(len(records), 2)
        self.assertFalse(records[0].terminal)
        self.assertTrue(records[0].retryable)
        self.assertEqual(records[0].attempt_index, 1)
        self.assertTrue(records[1].terminal)
        self.assertEqual(records[1].attempt_index, 2)
        self.assertEqual(records[1].status, "success")
        self.assertAlmostEqual(
            records[1].cumulative_latency_ms or 0,
            records[0].latency_ms + records[1].latency_ms,
        )
        self.assertEqual(summary["generation_invocations"], 2)
        self.assertEqual(summary["retry_attempts"], 1)
        self.assertEqual(summary["total_tasks"], 1)
        self.assertEqual(summary["successful_tasks"], 1)
        self.assertFalse(summary["formal_performance_run"])

    def test_timeout_is_retryable_and_preserves_deadline(self) -> None:
        class TimeoutThenSuccessAdapter:
            name = "deadline-aware"
            revision = "revision-1"

            def __init__(self) -> None:
                self.timeouts: list[float | None] = []

            def generate(
                self,
                task: EvaluationTask,
                *,
                timeout_seconds: float | None = None,
            ) -> ModelOutput:
                self.timeouts.append(timeout_seconds)
                if len(self.timeouts) == 1:
                    raise AdapterTimeoutError("deadline reached")
                return ModelOutput(
                    text="answer",
                    backend=self.name,
                    model_revision=self.revision,
                )

        adapter = TimeoutThenSuccessAdapter()
        task = EvaluationTask(id="timeout", prompt="Return.")
        with tempfile.TemporaryDirectory() as temp_dir:
            records = run_benchmark(
                [task],
                adapter,
                Path(temp_dir) / "run.jsonl",
                max_retries=1,
                timeout_seconds=0.25,
            )

        self.assertEqual(adapter.timeouts, [0.25, 0.25])
        self.assertEqual(
            [record.status for record in records],
            ["timeout", "success"],
        )
        self.assertEqual(
            [record.terminal for record in records],
            [False, True],
        )
        self.assertTrue(all(record.timeout_seconds == 0.25 for record in records))
        self.assertTrue(all(record.max_retries == 1 for record in records))

    def test_retry_exhaustion_counts_one_terminal_failure(self) -> None:
        class AlwaysFailingAdapter:
            name = "always-failing"
            revision = "revision-1"

            def generate(self, task: EvaluationTask) -> ModelOutput:
                raise RuntimeError("still failing")

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark(
                [EvaluationTask(id="failure", prompt="Fail.")],
                AlwaysFailingAdapter(),
                output,
                max_retries=2,
            )
            summary = summarize(load_records(output))

        self.assertEqual(len(records), 3)
        self.assertEqual(
            [record.terminal for record in records],
            [False, False, True],
        )
        self.assertEqual(summary["retry_attempts"], 2)
        self.assertEqual(summary["total_tasks"], 1)
        self.assertEqual(summary["successful_tasks"], 0)
        self.assertEqual(summary["failures"], {"generation_error": 1})

    def test_retry_configuration_rejects_invalid_values(self) -> None:
        task = EvaluationTask(id="validation", prompt="Validate.")
        invalid_configs = (
            ({"max_retries": -1}, "max_retries"),
            ({"max_retries": True}, "max_retries"),
            ({"max_retries": 1.5}, "max_retries"),
            ({"timeout_seconds": 0}, "timeout_seconds"),
            ({"timeout_seconds": float("inf")}, "timeout_seconds"),
            ({"timeout_seconds": True}, "timeout_seconds"),
        )
        for configuration, message in invalid_configs:
            with self.subTest(configuration=configuration):
                with tempfile.TemporaryDirectory() as temp_dir:
                    with self.assertRaisesRegex(ValueError, message):
                        run_benchmark(
                            [task],
                            MockAdapter(),
                            Path(temp_dir) / "run.jsonl",
                            **configuration,
                        )

    def test_resume_continues_an_unfinished_retry_chain(self) -> None:
        class InterruptedRetryAdapter:
            name = "retry-resume"
            revision = "revision-1"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: EvaluationTask) -> ModelOutput:
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("retry me")
                raise KeyboardInterrupt()

        class ResumedAdapter:
            name = "retry-resume"
            revision = "revision-1"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: EvaluationTask) -> ModelOutput:
                self.calls += 1
                return ModelOutput(
                    text="answer",
                    backend=self.name,
                    model_revision=self.revision,
                )

        task = EvaluationTask(id="retry-resume", prompt="Return.")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            with self.assertRaises(KeyboardInterrupt):
                run_benchmark(
                    [task],
                    InterruptedRetryAdapter(),
                    output,
                    max_retries=1,
                )

            partial = load_records(output)
            resumed_adapter = ResumedAdapter()
            records = run_benchmark(
                [task],
                resumed_adapter,
                output,
                max_retries=1,
                resume=True,
            )

        self.assertEqual(len(partial), 1)
        self.assertFalse(partial[0]["terminal"])
        self.assertEqual(resumed_adapter.calls, 1)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[-1].attempt_index, 2)
        self.assertTrue(records[-1].terminal)

    def test_resume_rejects_a_changed_retry_policy(self) -> None:
        class FailingThenInterruptingAdapter:
            name = "retry-policy"
            revision = "revision-1"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: EvaluationTask) -> ModelOutput:
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("retry me")
                raise KeyboardInterrupt()

        class CompatibleAdapter:
            name = "retry-policy"
            revision = "revision-1"

            def generate(self, task: EvaluationTask) -> ModelOutput:
                return ModelOutput(
                    text="answer",
                    backend=self.name,
                    model_revision=self.revision,
                )

        task = EvaluationTask(id="retry-policy", prompt="Return.")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            with self.assertRaises(KeyboardInterrupt):
                run_benchmark(
                    [task],
                    FailingThenInterruptingAdapter(),
                    output,
                    max_retries=1,
                )

            with self.assertRaisesRegex(ResumeError, "max_retries"):
                run_benchmark(
                    [task],
                    CompatibleAdapter(),
                    output,
                    max_retries=0,
                    resume=True,
                )

    def test_typed_adapter_failure_keeps_specific_status(self) -> None:
        class OutOfMemoryAdapter:
            name = "memory-limited"
            revision = "revision-1"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: EvaluationTask):
                self.calls += 1
                raise AdapterOutOfMemoryError("CUDA out of memory")

        task = EvaluationTask(id="failure", prompt="Fail specifically.")
        adapter = OutOfMemoryAdapter()
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark(
                [task],
                adapter,
                output,
                max_retries=3,
            )

        self.assertEqual(adapter.calls, 1)
        self.assertEqual(records[0].status, "out_of_memory")
        self.assertEqual(records[0].model_revision, "revision-1")

    def test_resume_appends_only_missing_attempts(self) -> None:
        class InterruptingAdapter:
            name = "stable"
            revision = "revision-1"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: EvaluationTask) -> ModelOutput:
                self.calls += 1
                if self.calls == 2:
                    raise KeyboardInterrupt()
                return ModelOutput(
                    text=task.id,
                    backend=self.name,
                    model_revision=self.revision,
                )

        class ResumedAdapter:
            name = "stable"
            revision = "revision-1"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: EvaluationTask) -> ModelOutput:
                self.calls += 1
                return ModelOutput(
                    text=task.id,
                    backend=self.name,
                    model_revision=self.revision,
                )

        tasks = [
            EvaluationTask(id="task-1", prompt="First."),
            EvaluationTask(id="task-2", prompt="Second."),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            with self.assertRaises(KeyboardInterrupt):
                run_benchmark(
                    tasks,
                    InterruptingAdapter(),
                    output,
                    repetitions=2,
                )

            resumed_adapter = ResumedAdapter()
            checkpoint_sizes: list[int] = []
            records = run_benchmark(
                tasks,
                resumed_adapter,
                output,
                repetitions=2,
                resume=True,
                on_record_persisted=lambda current: checkpoint_sizes.append(
                    len(current)
                ),
            )
            loaded = load_records(output)

        self.assertEqual(resumed_adapter.calls, 3)
        self.assertEqual(checkpoint_sizes, [2, 3, 4])
        self.assertEqual(len(records), 4)
        self.assertEqual(len(loaded), 4)
        self.assertEqual(
            [
                (record["task_id"], record["repetition"])
                for record in loaded
            ],
            [
                ("task-1", 1),
                ("task-2", 1),
                ("task-1", 2),
                ("task-2", 2),
            ],
        )

    def test_each_record_is_synced_before_checkpoint(self) -> None:
        tasks = [
            EvaluationTask(id="task-1", prompt="First."),
            EvaluationTask(id="task-2", prompt="Second."),
        ]
        events: list[tuple[str, int]] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            with patch(
                "openmultimodal_lab.runner.os.fsync",
                side_effect=lambda descriptor: events.append(
                    ("sync", descriptor)
                ),
            ) as fsync:
                run_benchmark(
                    tasks,
                    MockAdapter(),
                    output,
                    on_record_persisted=lambda records: events.append(
                        ("checkpoint", len(records))
                    ),
                )

        self.assertEqual(fsync.call_count, 2)
        self.assertEqual(
            [event[0] for event in events],
            ["sync", "checkpoint", "sync", "checkpoint"],
        )

    def test_resume_rejects_truncated_jsonl_boundary(self) -> None:
        task = EvaluationTask(id="task-1", prompt="First.")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            run_benchmark([task], MockAdapter(), output)
            output.write_bytes(output.read_bytes().rstrip(b"\n"))

            with self.assertRaisesRegex(
                ResumeError,
                "durable JSONL record boundary",
            ):
                run_benchmark(
                    [task],
                    MockAdapter(),
                    output,
                    resume=True,
                )

    def test_resume_rejects_oversized_record(self) -> None:
        task = EvaluationTask(id="task-1", prompt="First.")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            run_benchmark([task], MockAdapter(), output)

            with patch(
                "openmultimodal_lab.runner.MAX_RESUME_RECORD_BYTES",
                4,
            ), self.assertRaisesRegex(ResumeError, "record safety limit"):
                run_benchmark(
                    [task],
                    MockAdapter(),
                    output,
                    resume=True,
                )

    def test_resume_rejects_changed_attempt_plan(self) -> None:
        tasks = [
            EvaluationTask(id="task-1", prompt="First."),
            EvaluationTask(id="task-2", prompt="Second."),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            run_benchmark(tasks, MockAdapter(), output)

            with self.assertRaisesRegex(
                ResumeError,
                "not the expected run prefix",
            ):
                run_benchmark(
                    list(reversed(tasks)),
                    MockAdapter(),
                    output,
                    resume=True,
                )

    def test_resume_rejects_changed_reference_contract(self) -> None:
        original = EvaluationTask(
            id="task-1",
            prompt="First.",
            expected_keywords=("first",),
        )
        changed = EvaluationTask(
            id="task-1",
            prompt="First.",
            expected_keywords=("different",),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            run_benchmark([original], MockAdapter(), output)

            with self.assertRaisesRegex(
                ResumeError,
                "expected_keywords",
            ):
                run_benchmark(
                    [changed],
                    MockAdapter(),
                    output,
                    resume=True,
                )

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

    def test_warmup_and_repetitions_are_recorded_but_scored_separately(
        self,
    ) -> None:
        tasks = [
            EvaluationTask(
                id="task-1",
                prompt="First.",
                expected_keywords=("first",),
            ),
            EvaluationTask(
                id="task-2",
                prompt="Second.",
                expected_keywords=("second",),
            ),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "run.jsonl"
            records = run_benchmark(
                tasks,
                MockAdapter(),
                output,
                warmup=1,
                repetitions=3,
            )
            loaded = load_records(output)
            summary = summarize(loaded)

        self.assertEqual(len(records), 7)
        self.assertEqual(records[0].phase, "warmup")
        self.assertIsNone(records[0].score)
        self.assertEqual(
            [record.repetition for record in records[1:]],
            [1, 1, 2, 2, 3, 3],
        )
        self.assertEqual(summary["total_records"], 7)
        self.assertEqual(summary["warmup_attempts"], 1)
        self.assertEqual(summary["total_tasks"], 6)
        self.assertEqual(summary["unique_tasks"], 2)
        self.assertEqual(summary["repetitions"], 3)
        self.assertEqual(summary["mean_score"], 1.0)
        self.assertFalse(summary["formal_performance_run"])

    def test_summary_excludes_warmup_from_performance_metrics(self) -> None:
        records = [
            {
                "phase": "warmup",
                "repetition": 1,
                "task_id": "task-1",
                "status": "success",
                "latency_ms": 9999,
                "score": None,
                "usage": {
                    "model_load_ms": 12000,
                    "ttft_ms": 9999,
                    "output_tokens_per_second": 1,
                    "peak_gpu_memory_mb": 9999,
                },
            },
            {
                "phase": "measurement",
                "repetition": 1,
                "task_id": "task-1",
                "status": "success",
                "latency_ms": 100,
                "score": 1,
                "usage": {
                    "preprocessing_ms": 10,
                    "ttft_ms": 20,
                    "generation_ms": 50,
                    "output_tokens_per_second": 40,
                    "decode_tokens_per_second": 60,
                    "peak_gpu_memory_mb": 4000,
                },
            },
            {
                "phase": "measurement",
                "repetition": 2,
                "task_id": "task-1",
                "status": "success",
                "latency_ms": 200,
                "score": 0,
                "usage": {
                    "preprocessing_ms": 20,
                    "ttft_ms": 40,
                    "generation_ms": 100,
                    "output_tokens_per_second": 20,
                    "decode_tokens_per_second": 30,
                    "peak_gpu_memory_mb": 4100,
                },
            },
        ]

        summary = summarize(records)

        self.assertEqual(summary["median_latency_ms"], 150)
        self.assertEqual(summary["median_ttft_ms"], 30)
        self.assertEqual(summary["p95_ttft_ms"], 40)
        self.assertEqual(summary["median_preprocessing_ms"], 15)
        self.assertEqual(summary["model_load_ms"], 12000)
        self.assertEqual(summary["median_generation_ms"], 75)
        self.assertEqual(summary["median_output_tokens_per_second"], 30)
        self.assertEqual(summary["median_decode_tokens_per_second"], 45)
        self.assertEqual(summary["peak_gpu_memory_mb"], 4100)
        self.assertTrue(summary["performance_metrics_complete"])
        self.assertFalse(summary["formal_performance_run"])

    def test_summary_treats_legacy_records_as_single_measurement(self) -> None:
        summary = summarize(
            [
                {
                    "schema_version": "0.2",
                    "task_id": "legacy-task",
                    "status": "success",
                    "latency_ms": 25,
                    "score": 1,
                    "usage": {},
                }
            ]
        )

        self.assertEqual(summary["total_records"], 1)
        self.assertEqual(summary["warmup_attempts"], 0)
        self.assertEqual(summary["total_tasks"], 1)
        self.assertEqual(summary["unique_tasks"], 1)
        self.assertEqual(summary["repetitions"], 1)

    def test_summary_marks_only_complete_three_repeat_run_as_formal(self) -> None:
        usage = {
            "preprocessing_ms": 5,
            "ttft_ms": 10,
            "generation_ms": 20,
            "output_tokens_per_second": 30,
            "peak_gpu_memory_mb": 4000,
        }
        records = [
            {
                "phase": "warmup",
                "repetition": 1,
                "task_id": "task-1",
                "status": "success",
                "latency_ms": 100,
                "score": None,
                "usage": usage,
            },
            *[
                {
                    "phase": "measurement",
                    "repetition": repetition,
                    "task_id": "task-1",
                    "status": "success",
                    "latency_ms": 25,
                    "score": 1,
                    "usage": usage,
                }
                for repetition in (1, 2, 3)
            ],
        ]

        summary = summarize(records)

        self.assertTrue(summary["performance_metrics_complete"])
        self.assertTrue(summary["formal_performance_run"])

    def test_summary_rejects_measurement_model_reload_as_formal(self) -> None:
        def usage(*, model_load_ms: float) -> dict[str, float]:
            return {
                "model_load_ms": model_load_ms,
                "preprocessing_ms": 5,
                "ttft_ms": 10,
                "generation_ms": 20,
                "output_tokens_per_second": 30,
                "peak_gpu_memory_mb": 4000,
            }

        records = [
            {
                "phase": "warmup",
                "repetition": 1,
                "task_id": "task-1",
                "status": "success",
                "latency_ms": 100,
                "score": None,
                "usage": usage(model_load_ms=12000),
            },
            *[
                {
                    "phase": "measurement",
                    "repetition": repetition,
                    "task_id": "task-1",
                    "status": "success",
                    "latency_ms": 25,
                    "score": 1,
                    "usage": usage(
                        model_load_ms=5000 if repetition == 2 else 0
                    ),
                }
                for repetition in (1, 2, 3)
            ],
        ]

        summary = summarize(records)

        self.assertTrue(summary["performance_metrics_complete"])
        self.assertEqual(summary["measurement_model_reloads"], 1)
        self.assertFalse(summary["formal_performance_run"])


if __name__ == "__main__":
    unittest.main()

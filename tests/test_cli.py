from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openmultimodal_lab.adapters.errors import AdapterTimeoutError
from openmultimodal_lab.cli import _hugging_face_cache_path, main
from openmultimodal_lab.manifest import manifest_path_for
from openmultimodal_lab.models import ModelOutput
from openmultimodal_lab.reporting import load_records


class RunCommandTests(unittest.TestCase):
    def _write_dataset(self, path: Path) -> None:
        tasks = [
            {
                "schema_version": "1.0",
                "id": "image-1",
                "prompt": "Describe the image.",
                "metadata": {"category": "image-description"},
            },
            {
                "schema_version": "1.0",
                "id": "document-1",
                "prompt": "Read the document.",
                "metadata": {"category": "document"},
            },
            {
                "schema_version": "1.0",
                "id": "spatial-1",
                "prompt": "Reason about the layout.",
                "metadata": {"category": "spatial-reasoning"},
            },
        ]
        path.write_text(
            "".join(json.dumps(task) + "\n" for task in tasks),
            encoding="utf-8",
        )

    def test_run_filters_one_or_more_categories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)

            with (
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                        "--category",
                        "image-description",
                        "--category",
                        "spatial-reasoning",
                    ]
                )

            records = load_records(output)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [record["task_id"] for record in records],
            ["image-1", "spatial-1"],
        )

    def test_run_rejects_category_without_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)
            stderr = io.StringIO()

            with (
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                        "--category",
                        "video",
                    ]
                )

            output_exists = output.exists()

        self.assertEqual(exit_code, 2)
        self.assertFalse(output_exists)
        self.assertIn("No tasks matched categories: video", stderr.getvalue())
        self.assertIn(
            "Available: document, image-description, spatial-reasoning",
            stderr.getvalue(),
        )

    def test_run_writes_manifest_for_warmup_and_repetitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)

            with (
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="Test GPU, 8192 MiB, driver",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                        "--warmup",
                        "1",
                        "--repetitions",
                        "2",
                    ]
                )

            records = load_records(output)
            manifest = json.loads(
                manifest_path_for(output).read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(records), 7)
        self.assertEqual(records[0]["phase"], "warmup")
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["records_written"], 7)
        self.assertEqual(manifest["warmup_records"], 1)
        self.assertEqual(manifest["measurement_records"], 6)
        self.assertEqual(manifest["protocol"]["repetitions"], 2)
        self.assertEqual(manifest["protocol"]["max_retries"], 0)
        self.assertIsNone(manifest["protocol"]["attempt_timeout_seconds"])
        self.assertEqual(
            manifest["environment"]["gpu"],
            "Test GPU, 8192 MiB, driver",
        )

    def test_run_persists_retry_and_timeout_configuration(self) -> None:
        class TimeoutThenSuccessAdapter:
            name = "mock"
            revision = "retry-test"
            model_id = "mock"

            def __init__(self) -> None:
                self.calls = 0

            def generate(
                self,
                task: object,
                *,
                timeout_seconds: float | None = None,
            ) -> ModelOutput:
                self.calls += 1
                self.timeout_seconds = timeout_seconds
                if self.calls == 1:
                    raise AdapterTimeoutError("injected timeout")
                return ModelOutput(
                    text="generated",
                    backend=self.name,
                    model_revision=self.revision,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)
            adapter = TimeoutThenSuccessAdapter()
            with (
                patch(
                    "openmultimodal_lab.cli.create_adapter",
                    return_value=adapter,
                ),
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                        "--attempt-timeout-seconds",
                        "0.25",
                        "--max-retries",
                        "1",
                    ]
                )

            records = load_records(output)
            manifest = json.loads(
                manifest_path_for(output).read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(adapter.calls, 4)
        self.assertEqual(adapter.timeout_seconds, 0.25)
        self.assertEqual(len(records), 4)
        self.assertFalse(records[0]["terminal"])
        self.assertEqual(records[1]["attempt_index"], 2)
        self.assertEqual(manifest["records_written"], 4)
        self.assertEqual(manifest["generation_invocations"], 4)
        self.assertEqual(manifest["retry_records"], 1)
        self.assertEqual(manifest["measurement_records"], 3)
        self.assertEqual(manifest["protocol"]["max_retries"], 1)
        self.assertEqual(
            manifest["protocol"]["attempt_timeout_seconds"],
            0.25,
        )

    def test_interrupted_run_manifest_counts_durable_partial_records(self) -> None:
        class InterruptingAdapter:
            name = "interrupting"
            revision = "test"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: object) -> ModelOutput:
                self.calls += 1
                if self.calls == 2:
                    raise KeyboardInterrupt()
                return ModelOutput(
                    text="generated",
                    backend=self.name,
                    model_revision=self.revision,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)

            with (
                patch(
                    "openmultimodal_lab.cli.create_adapter",
                    return_value=InterruptingAdapter(),
                ),
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(KeyboardInterrupt),
            ):
                main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                    ]
                )

            records = load_records(output)
            manifest = json.loads(
                manifest_path_for(output).read_text(encoding="utf-8")
            )
            output_size = output.stat().st_size

        self.assertEqual(len(records), 1)
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["records_written"], 1)
        self.assertEqual(manifest["measurement_records"], 1)
        self.assertEqual(manifest["error"], "KeyboardInterrupt: ")
        self.assertEqual(
            manifest["output"]["size_bytes"],
            output_size,
        )
        self.assertEqual(len(manifest["output"]["sha256"]), 64)

    def test_run_refuses_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)

            with (
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                first_exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                    ]
                )
            original = output.read_bytes()
            stderr = io.StringIO()
            with (
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                second_exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                    ]
                )

            unchanged = output.read_bytes()
            resume_stderr = io.StringIO()
            with (
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(resume_stderr),
            ):
                resume_exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )

        self.assertEqual(first_exit_code, 0)
        self.assertEqual(second_exit_code, 2)
        self.assertEqual(resume_exit_code, 2)
        self.assertEqual(unchanged, original)
        self.assertIn(
            "output or manifest already exists",
            stderr.getvalue(),
        )
        self.assertIn(
            "only started or failed runs can resume",
            resume_stderr.getvalue(),
        )

    def test_run_resumes_interrupted_prefix_without_duplicates(self) -> None:
        class InterruptingAdapter:
            name = "mock"
            revision = "resume-test"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: object) -> ModelOutput:
                self.calls += 1
                if self.calls == 2:
                    raise KeyboardInterrupt()
                return ModelOutput(
                    text="generated",
                    backend=self.name,
                    model_revision=self.revision,
                )

        class ResumedAdapter:
            name = "mock"
            revision = "resume-test"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: object) -> ModelOutput:
                self.calls += 1
                return ModelOutput(
                    text="generated",
                    backend=self.name,
                    model_revision=self.revision,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)
            interrupted = InterruptingAdapter()

            with (
                patch(
                    "openmultimodal_lab.cli.create_adapter",
                    return_value=interrupted,
                ),
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(KeyboardInterrupt),
            ):
                main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                    ]
                )

            resumed = ResumedAdapter()
            with (
                patch(
                    "openmultimodal_lab.cli.create_adapter",
                    return_value=resumed,
                ),
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )

            records = load_records(output)
            manifest = json.loads(
                manifest_path_for(output).read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(resumed.calls, 2)
        self.assertEqual(len(records), 3)
        self.assertEqual(
            [record["task_id"] for record in records],
            ["image-1", "document-1", "spatial-1"],
        )
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["resume_count"], 1)
        self.assertEqual(manifest["records_written"], 3)
        self.assertEqual(len(manifest["output"]["sha256"]), 64)

    def test_resume_rejects_tampered_output_before_adapter_call(self) -> None:
        class InterruptingAdapter:
            name = "mock"
            revision = "resume-test"

            def __init__(self) -> None:
                self.calls = 0

            def generate(self, task: object) -> ModelOutput:
                self.calls += 1
                if self.calls == 2:
                    raise KeyboardInterrupt()
                return ModelOutput(
                    text="generated",
                    backend=self.name,
                    model_revision=self.revision,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            output = root / "run.jsonl"
            self._write_dataset(dataset)
            interrupted = InterruptingAdapter()

            with (
                patch(
                    "openmultimodal_lab.cli.create_adapter",
                    return_value=interrupted,
                ),
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
                self.assertRaises(KeyboardInterrupt),
            ):
                main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                    ]
                )

            output.write_bytes(output.read_bytes() + b" ")
            manifest_before = manifest_path_for(output).read_bytes()
            stderr = io.StringIO()
            with (
                patch(
                    "openmultimodal_lab.cli.create_adapter",
                    return_value=InterruptingAdapter(),
                ),
                patch(
                    "openmultimodal_lab.cli._gpu_summary",
                    return_value="not detected",
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "run",
                        "--dataset",
                        str(dataset),
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )
            manifest_after = manifest_path_for(output).read_bytes()

        self.assertEqual(exit_code, 2)
        self.assertEqual(manifest_after, manifest_before)
        self.assertIn("output size", stderr.getvalue())


class ReportCommandTests(unittest.TestCase):
    def test_report_returns_stable_error_for_invalid_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "invalid.jsonl"
            source.write_text(
                '{"task_id":"x","status":"success","latency_ms":1,'
                '"cumulative_latency_ms":"bad","score":1,"usage":{}}\n',
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main(["report", "--input", str(source)])

        self.assertEqual(exit_code, 2)
        self.assertIn("Report error:", stderr.getvalue())
        self.assertIn("cumulative_latency_ms", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


class DoctorCommandTests(unittest.TestCase):
    def test_hugging_face_cache_path_respects_environment(self) -> None:
        cases = (
            (
                {
                    "HF_HUB_CACHE": "custom-hub-cache",
                    "HF_HOME": "ignored-home",
                    "XDG_CACHE_HOME": "ignored-xdg-cache",
                },
                Path("custom-hub-cache"),
            ),
            (
                {
                    "HF_HOME": "custom-home",
                    "XDG_CACHE_HOME": "ignored-xdg-cache",
                },
                Path("custom-home") / "hub",
            ),
            (
                {"XDG_CACHE_HOME": "custom-xdg-cache"},
                Path("custom-xdg-cache") / "huggingface" / "hub",
            ),
        )
        for environment, expected in cases:
            with self.subTest(environment=environment):
                with patch.dict(os.environ, environment, clear=True):
                    cache_path = _hugging_face_cache_path()

                self.assertEqual(cache_path, expected)

    def test_core_doctor_reports_disk_without_making_it_a_dependency(self) -> None:
        stdout = io.StringIO()
        with (
            patch(
                "openmultimodal_lab.cli._gpu_summary",
                return_value="not detected",
            ),
            patch(
                "openmultimodal_lab.cli._disk_free_gib",
                return_value=None,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = main(["doctor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Working disk free: unavailable", stdout.getvalue())

    def test_qwen_doctor_warns_about_low_model_cache_disk(self) -> None:
        fake_torch = SimpleNamespace(
            __version__="2.13.0+cu130",
            version=SimpleNamespace(cuda="13.0"),
            cuda=SimpleNamespace(is_available=lambda: True),
        )
        stdout = io.StringIO()
        with (
            patch(
                "openmultimodal_lab.cli._gpu_summary",
                return_value="NVIDIA RTX Test GPU, 8192 MiB, driver",
            ),
            patch(
                "openmultimodal_lab.cli._disk_free_gib",
                side_effect=(100.0, 2.0),
            ),
            patch(
                "openmultimodal_lab.cli.importlib.util.find_spec",
                return_value=object(),
            ),
            patch(
                "openmultimodal_lab.cli.importlib.import_module",
                return_value=fake_torch,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = main(["doctor", "--backend", "qwen3-vl"])

        self.assertEqual(exit_code, 0)
        self.assertIn("cache disk free: 2.0 GiB", stdout.getvalue())
        self.assertIn("recommends at least 8.0 GiB", stdout.getvalue())

    def test_detects_cpu_only_torch_when_nvidia_gpu_exists(self) -> None:
        fake_torch = SimpleNamespace(
            __version__="2.13.0+cpu",
            version=SimpleNamespace(cuda=None),
            cuda=SimpleNamespace(is_available=lambda: False),
        )
        stdout = io.StringIO()

        with (
            patch(
                "openmultimodal_lab.cli._gpu_summary",
                return_value="NVIDIA RTX Test GPU, 8192 MiB, driver",
            ),
            patch(
                "openmultimodal_lab.cli.importlib.util.find_spec",
                return_value=object(),
            ),
            patch(
                "openmultimodal_lab.cli.importlib.import_module",
                return_value=fake_torch,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = main(["doctor", "--backend", "qwen3-vl"])

        self.assertEqual(exit_code, 1)
        self.assertIn("PyTorch CUDA build: none", stdout.getvalue())
        self.assertIn("GPU runtime is not ready", stdout.getvalue())

    def test_smolvlm2_doctor_uses_its_own_install_instructions(self) -> None:
        stdout = io.StringIO()
        with (
            patch(
                "openmultimodal_lab.cli.importlib.util.find_spec",
                return_value=None,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = main(["doctor", "--backend", "smolvlm2"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Missing SmolVLM2 modules", stdout.getvalue())
        self.assertIn('".[smolvlm2]"', stdout.getvalue())

    def test_smolvlm2_doctor_rejects_gpu_without_bf16(self) -> None:
        fake_torch = SimpleNamespace(
            __version__="2.13.0+cu130",
            version=SimpleNamespace(cuda="13.0"),
            cuda=SimpleNamespace(
                is_available=lambda: True,
                is_bf16_supported=lambda: False,
            ),
        )
        stdout = io.StringIO()
        with (
            patch(
                "openmultimodal_lab.cli._gpu_summary",
                return_value="NVIDIA Test GPU, 4096 MiB, driver",
            ),
            patch(
                "openmultimodal_lab.cli.importlib.util.find_spec",
                return_value=object(),
            ),
            patch(
                "openmultimodal_lab.cli.importlib.import_module",
                return_value=fake_torch,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = main(["doctor", "--backend", "smolvlm2"])

        self.assertEqual(exit_code, 1)
        self.assertIn("CUDA BF16 supported: no", stdout.getvalue())
        self.assertIn("requires native BF16", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openmultimodal_lab.cli import main
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
        self.assertEqual(
            manifest["environment"]["gpu"],
            "Test GPU, 8192 MiB, driver",
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

        self.assertEqual(len(records), 1)
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["records_written"], 1)
        self.assertEqual(manifest["measurement_records"], 1)
        self.assertEqual(manifest["error"], "KeyboardInterrupt: ")


class DoctorCommandTests(unittest.TestCase):
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

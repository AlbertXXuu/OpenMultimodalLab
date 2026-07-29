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

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
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

            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
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


if __name__ == "__main__":
    unittest.main()

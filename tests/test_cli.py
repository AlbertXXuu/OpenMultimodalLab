from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()

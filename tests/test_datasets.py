from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from openmultimodal_lab.datasets import DatasetError, load_tasks


class LoadTasksTests(unittest.TestCase):
    def test_loads_valid_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            media = root / "image.svg"
            media.write_text("<svg/>", encoding="utf-8")
            dataset = root / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "id": "task-1",
                        "prompt": "Describe the image.",
                        "media": ["image.svg"],
                        "expected_keywords": ["shape"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            tasks = load_tasks(dataset, media_root=root)

            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].id, "task-1")
            self.assertEqual(tasks[0].schema_version, "1.0")

    def test_rejects_duplicate_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            item = {
                "schema_version": "1.0",
                "id": "duplicate",
                "prompt": "Prompt",
            }
            dataset.write_text(
                json.dumps(item) + "\n" + json.dumps(item) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "duplicate task id"):
                load_tasks(dataset)

    def test_rejects_missing_media(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "id": "missing-media",
                        "prompt": "Prompt",
                        "media": ["missing.png"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "does not exist"):
                load_tasks(dataset, media_root=root)

    def test_rejects_missing_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps({"id": "task-1", "prompt": "Prompt"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "schema_version"):
                load_tasks(dataset)

    def test_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "9.9",
                        "id": "task-1",
                        "prompt": "Prompt",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DatasetError, "unsupported schema version"
            ):
                load_tasks(dataset)

    def test_validation_error_includes_line_and_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "id": "broken-prompt",
                        "prompt": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DatasetError,
                r"tasks\.jsonl:1: task 'broken-prompt'",
            ):
                load_tasks(dataset)


if __name__ == "__main__":
    unittest.main()

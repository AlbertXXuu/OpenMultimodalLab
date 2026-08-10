from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openmultimodal_lab.datasets import DatasetError, load_tasks


class LoadTasksTests(unittest.TestCase):
    def test_rejects_dataset_above_safety_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "oversized.jsonl"
            dataset.write_bytes(b"x" * 11)

            with patch(
                "openmultimodal_lab.datasets.MAX_DATASET_BYTES",
                10,
            ), self.assertRaisesRegex(DatasetError, "safety limit"):
                load_tasks(dataset)

    def test_rejects_oversized_jsonl_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "long-line.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "id": "long",
                        "prompt": "x" * 100,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with patch(
                "openmultimodal_lab.datasets.MAX_JSONL_LINE_BYTES",
                32,
            ), self.assertRaisesRegex(DatasetError, "JSONL line exceeds"):
                load_tasks(dataset)

    def test_rejects_non_utf8_with_line_number(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "encoding.jsonl"
            dataset.write_bytes(b"{}\n\xff\n")

            with self.assertRaisesRegex(
                DatasetError,
                r"encoding\.jsonl:2: dataset is not valid UTF-8",
            ):
                load_tasks(dataset)

    def test_rejects_nonstandard_json_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "nonstandard.jsonl"
            dataset.write_text(
                '{"schema_version":"1.0","id":"bad","prompt":"x",'
                '"metadata":{"value":NaN}}\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DatasetError,
                "non-standard JSON numeric constant 'NaN'",
            ):
                load_tasks(dataset, require_media=False)

    def test_rejects_blank_media_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "blank-media.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "id": "blank-media",
                        "prompt": "Prompt",
                        "media": ["  "],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "non-empty strings"):
                load_tasks(dataset, require_media=False)

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

    def test_loads_schema_v1_1_structured_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "id": "structured",
                        "prompt": "Describe the shapes.",
                        "expected_keywords": ["red circle"],
                        "scoring": {
                            "type": "attribute_groups",
                            "groups": [["red", "circle"]],
                            "ordered": False,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            tasks = load_tasks(dataset)

        self.assertEqual(tasks[0].schema_version, "1.1")
        self.assertEqual(tasks[0].scoring.type, "attribute_groups")
        self.assertEqual(tasks[0].scoring.groups, (("red", "circle"),))

    def test_schema_v1_1_requires_scoring_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "id": "missing-scoring",
                        "prompt": "Prompt",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "'scoring' must be an object"):
                load_tasks(dataset)

    def test_rejects_mismatched_attribute_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "id": "mismatched-groups",
                        "prompt": "Prompt",
                        "expected_keywords": ["red circle", "blue square"],
                        "scoring": {
                            "type": "attribute_groups",
                            "groups": [["red", "circle"]],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "must have equal length"):
                load_tasks(dataset)

    def test_rejects_invalid_or_duplicate_scoring_references(self) -> None:
        invalid_cases = (
            (
                {
                    "type": "normalized_exact_match",
                    "groups": "not-a-list",
                },
                ["red"],
                "must be a list",
            ),
            (
                {
                    "type": "attribute_groups",
                    "groups": [["red", "RED"]],
                },
                ["red object"],
                "duplicate terms",
            ),
            (
                {
                    "type": "normalized_exact_match",
                },
                ["yes", "YES"],
                "must not contain duplicates",
            ),
        )
        for scoring, keywords, message in invalid_cases:
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as temp_dir:
                    dataset = Path(temp_dir) / "invalid-scoring.jsonl"
                    dataset.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.1",
                                "id": "invalid-scoring",
                                "prompt": "Prompt",
                                "expected_keywords": keywords,
                                "scoring": scoring,
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )

                    with self.assertRaisesRegex(DatasetError, message):
                        load_tasks(dataset, require_media=False)

    def test_loads_schema_v1_2_numeric_tolerance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.2",
                        "id": "numeric",
                        "prompt": "Return one number.",
                        "scoring": {
                            "type": "numeric_tolerance",
                            "target": 8.37,
                            "absolute_tolerance": 0.01,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            tasks = load_tasks(dataset)

        self.assertEqual(tasks[0].schema_version, "1.2")
        self.assertEqual(tasks[0].scoring.target, 8.37)
        self.assertEqual(tasks[0].scoring.absolute_tolerance, 0.01)

    def test_numeric_tolerance_requires_schema_v1_2(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "id": "numeric",
                        "prompt": "Return one number.",
                        "scoring": {
                            "type": "numeric_tolerance",
                            "target": 8.37,
                            "absolute_tolerance": 0.01,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "requires schema_version"):
                load_tasks(dataset)

    def test_numeric_tolerance_rejects_invalid_reference_fields(self) -> None:
        invalid_values = (
            (True, 0.01, "finite number"),
            (8.37, -0.01, "at least 0"),
            (
                8.37,
                float("inf"),
                "non-standard JSON numeric constant 'Infinity'",
            ),
        )
        for target, tolerance, message in invalid_values:
            with self.subTest(target=target, tolerance=tolerance):
                with tempfile.TemporaryDirectory() as temp_dir:
                    dataset = Path(temp_dir) / "tasks.jsonl"
                    dataset.write_text(
                        json.dumps(
                            {
                                "schema_version": "1.2",
                                "id": "numeric",
                                "prompt": "Return one number.",
                                "scoring": {
                                    "type": "numeric_tolerance",
                                    "target": target,
                                    "absolute_tolerance": tolerance,
                                },
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )

                    with self.assertRaisesRegex(DatasetError, message):
                        load_tasks(dataset)

    def test_numeric_tolerance_rejects_expected_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "tasks.jsonl"
            dataset.write_text(
                json.dumps(
                    {
                        "schema_version": "1.2",
                        "id": "numeric",
                        "prompt": "Return one number.",
                        "expected_keywords": ["8.37"],
                        "scoring": {
                            "type": "numeric_tolerance",
                            "target": 8.37,
                            "absolute_tolerance": 0.01,
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DatasetError, "must be empty"):
                load_tasks(dataset)


if __name__ == "__main__":
    unittest.main()

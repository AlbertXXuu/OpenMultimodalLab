from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openmultimodal_lab.adapters import MockAdapter
from openmultimodal_lab.datasets import available_categories, load_tasks
from openmultimodal_lab.runner import run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DATASET = PROJECT_ROOT / "examples" / "tasks" / "synthetic-v1.jsonl"
SYNTHETIC_DATASET_V1_1 = (
    PROJECT_ROOT / "examples" / "tasks" / "synthetic-v1.1.jsonl"
)
SYNTHETIC_DOCS_DATASET = (
    PROJECT_ROOT / "examples" / "tasks" / "synthetic-docs-v1.jsonl"
)
SYNTHETIC_MEDIA = PROJECT_ROOT / "examples" / "assets" / "synthetic-v1"
GENERATOR = PROJECT_ROOT / "scripts" / "generate_synthetic_images.py"
SYNTHETIC_DOCS_MEDIA = (
    PROJECT_ROOT / "examples" / "assets" / "synthetic-docs-v1"
)
SYNTHETIC_DOCS_GENERATOR = (
    PROJECT_ROOT / "scripts" / "generate_synthetic_documents.py"
)


class SyntheticDatasetTests(unittest.TestCase):
    def test_synthetic_v1_has_ten_licensed_tasks(self) -> None:
        tasks = load_tasks(SYNTHETIC_DATASET, media_root=PROJECT_ROOT)

        self.assertEqual(len(tasks), 10)
        self.assertEqual(
            available_categories(tasks),
            [
                "counting",
                "image-description",
                "spatial-reasoning",
                "visual-comparison",
            ],
        )
        for task in tasks:
            self.assertEqual(task.metadata.get("source"), "project-generated")
            self.assertEqual(task.metadata.get("license"), "Apache-2.0")
            self.assertEqual(
                task.metadata.get("generator"),
                "scripts/generate_synthetic_images.py",
            )
            self.assertEqual(len(task.media), 1)
            self.assertTrue(task.media[0].endswith(".png"))

    def test_committed_images_match_the_generator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            generated_dir = Path(temp_dir) / "synthetic-v1"
            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--output-dir",
                    str(generated_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            committed_files = sorted(SYNTHETIC_MEDIA.glob("*.png"))
            generated_files = sorted(generated_dir.glob("*.png"))

            self.assertEqual(len(committed_files), 10)
            self.assertEqual(
                [path.name for path in committed_files],
                [path.name for path in generated_files],
            )
            for committed, generated in zip(
                committed_files,
                generated_files,
                strict=True,
            ):
                self.assertEqual(committed.read_bytes(), generated.read_bytes())

    def test_synthetic_v1_1_has_explicit_structured_scoring(self) -> None:
        tasks = load_tasks(SYNTHETIC_DATASET_V1_1, media_root=PROJECT_ROOT)

        self.assertEqual(len(tasks), 10)
        self.assertTrue(all(task.schema_version == "1.1" for task in tasks))
        self.assertTrue(
            all(
                task.metadata.get("dataset_version") == "synthetic-v1.1"
                for task in tasks
            )
        )
        self.assertEqual(
            {task.scoring.type for task in tasks},
            {"normalized_exact_match", "attribute_groups"},
        )
        shape_list = next(task for task in tasks if task.id == "shapes-multi-001")
        self.assertEqual(
            shape_list.expected_keywords[-1],
            "green square",
        )
        self.assertTrue(shape_list.scoring.ordered)

    def test_synthetic_docs_v1_has_reviewable_coverage(self) -> None:
        tasks = load_tasks(SYNTHETIC_DOCS_DATASET, media_root=PROJECT_ROOT)

        self.assertEqual(len(tasks), 32)
        self.assertTrue(all(task.schema_version == "1.2" for task in tasks))
        self.assertEqual(
            available_categories(tasks),
            ["chart-qa", "document-key-value", "document-ocr", "table-qa"],
        )
        self.assertEqual(
            {task.scoring.type for task in tasks},
            {"normalized_exact_match", "numeric_tolerance"},
        )
        category_counts: dict[str, int] = {}
        media_counts: dict[str, int] = {}
        for task in tasks:
            category = str(task.metadata.get("category"))
            category_counts[category] = category_counts.get(category, 0) + 1
            self.assertEqual(
                task.metadata.get("dataset_version"),
                "synthetic-docs-v1",
            )
            self.assertEqual(task.metadata.get("source"), "project-generated")
            self.assertEqual(task.metadata.get("license"), "Apache-2.0")
            self.assertEqual(
                task.metadata.get("generator"),
                "scripts/generate_synthetic_documents.py",
            )
            self.assertEqual(len(task.media), 1)
            media_counts[task.media[0]] = media_counts.get(task.media[0], 0) + 1
            if task.scoring.type == "numeric_tolerance":
                self.assertEqual(task.expected_keywords, ())
                self.assertIsNotNone(task.scoring.target)
                self.assertIsNotNone(task.scoring.absolute_tolerance)

        self.assertEqual(
            category_counts,
            {
                "chart-qa": 8,
                "document-key-value": 10,
                "document-ocr": 6,
                "table-qa": 8,
            },
        )
        self.assertEqual(len(media_counts), 8)
        self.assertEqual(set(media_counts.values()), {4})

    def test_committed_document_images_match_the_generator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            generated_dir = Path(temp_dir) / "synthetic-docs-v1"
            subprocess.run(
                [
                    sys.executable,
                    str(SYNTHETIC_DOCS_GENERATOR),
                    "--output-dir",
                    str(generated_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            committed_files = sorted(SYNTHETIC_DOCS_MEDIA.glob("*.png"))
            generated_files = sorted(generated_dir.glob("*.png"))

            self.assertEqual(len(committed_files), 8)
            self.assertEqual(
                [path.name for path in committed_files],
                [path.name for path in generated_files],
            )
            for committed, generated in zip(
                committed_files,
                generated_files,
                strict=True,
            ):
                self.assertEqual(committed.read_bytes(), generated.read_bytes())

    def test_synthetic_docs_v1_runs_all_scorers_end_to_end(self) -> None:
        tasks = load_tasks(SYNTHETIC_DOCS_DATASET, media_root=PROJECT_ROOT)
        with tempfile.TemporaryDirectory() as temp_dir:
            records = run_benchmark(
                tasks,
                MockAdapter(),
                Path(temp_dir) / "results.jsonl",
            )

        self.assertEqual(len(records), 32)
        self.assertTrue(all(record.status == "success" for record in records))
        self.assertTrue(all(record.score == 1.0 for record in records))


if __name__ == "__main__":
    unittest.main()

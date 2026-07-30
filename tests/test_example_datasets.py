from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openmultimodal_lab.datasets import available_categories, load_tasks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DATASET = PROJECT_ROOT / "examples" / "tasks" / "synthetic-v1.jsonl"
SYNTHETIC_DATASET_V1_1 = (
    PROJECT_ROOT / "examples" / "tasks" / "synthetic-v1.1.jsonl"
)
SYNTHETIC_MEDIA = PROJECT_ROOT / "examples" / "assets" / "synthetic-v1"
GENERATOR = PROJECT_ROOT / "scripts" / "generate_synthetic_images.py"


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


if __name__ == "__main__":
    unittest.main()

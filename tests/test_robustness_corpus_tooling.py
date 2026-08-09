from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import unittest
import zlib
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
CANONICAL_DATASET = (
    PROJECT_ROOT / "examples/tasks/synthetic-robustness-v1.jsonl"
)
CANONICAL_ASSETS = PROJECT_ROOT / "examples/assets/synthetic-robustness-v1"
CANONICAL_REVIEW = (
    PROJECT_ROOT / "docs/reviews/synthetic-robustness-v1.json"
)
CANONICAL_REVIEW_SHEET = (
    PROJECT_ROOT / "docs/reviews/synthetic-robustness-v1-overview.png"
)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from generate_robustness_images import (  # noqa: E402
    HEIGHT,
    REVIEW_CHECKS,
    SCENES,
    WIDTH,
    build_tasks,
    generate_assets,
    write_jsonl,
    write_review_template,
)
from validate_human_review import audit_human_review  # noqa: E402

from openmultimodal_lab.datasets import load_tasks  # noqa: E402


def _decode_rgb_png(path: Path) -> tuple[int, int, bytes]:
    value = path.read_bytes()
    if value[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("not a PNG file")
    offset = 8
    width = 0
    height = 0
    compressed = bytearray()
    while offset < len(value):
        length = struct.unpack_from(">I", value, offset)[0]
        chunk_type = value[offset + 4 : offset + 8]
        payload = value[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height = struct.unpack_from(">II", payload)
        elif chunk_type == b"IDAT":
            compressed.extend(payload)
        elif chunk_type == b"IEND":
            break
    raw = zlib.decompress(bytes(compressed))
    stride = width * 3
    rows: list[bytes] = []
    for row_index in range(height):
        row = raw[row_index * (stride + 1) : (row_index + 1) * (stride + 1)]
        if row[0] != 0:
            raise AssertionError("unexpected PNG row filter")
        rows.append(row[1:])
    return width, height, b"".join(rows)


def _pixel(pixels: bytes, x: int, y: int, width: int = WIDTH) -> tuple[int, ...]:
    offset = (y * width + x) * 3
    return tuple(pixels[offset : offset + 3])


class RobustnessCorpusToolingTests(unittest.TestCase):
    def test_canonical_corpus_is_deterministic_and_owner_reviewed(self) -> None:
        rows = [
            json.loads(line)
            for line in CANONICAL_DATASET.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        review = json.loads(CANONICAL_REVIEW.read_text(encoding="utf-8"))
        findings = audit_human_review(CANONICAL_DATASET, CANONICAL_REVIEW)
        tasks = load_tasks(CANONICAL_DATASET, media_root=PROJECT_ROOT)

        self.assertEqual(
            rows,
            build_tasks(
                "synthetic-robustness-v1",
                "examples/assets/synthetic-robustness-v1",
            ),
        )
        self.assertEqual(len(tasks), 36)
        self.assertEqual(
            review["dataset_sha256"],
            hashlib.sha256(CANONICAL_DATASET.read_bytes()).hexdigest(),
        )
        self.assertEqual(findings, [])
        self.assertTrue(
            all(
                value is True
                for entry in review["entries"]
                for value in entry["checks"].values()
            )
        )
        self.assertTrue(
            all(
                entry["reviewer"] == "AlbertXXuu"
                for entry in review["entries"]
            )
        )
        self.assertTrue(
            all(
                entry["reviewed_at"] == "2026-08-10"
                for entry in review["entries"]
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            generate_assets(
                root / "assets",
                review_sheet=root / "overview.png",
            )
            for path in CANONICAL_ASSETS.iterdir():
                self.assertEqual(
                    path.read_bytes(),
                    (root / "assets" / path.name).read_bytes(),
                )
            self.assertEqual(
                CANONICAL_REVIEW_SHEET.read_bytes(),
                (root / "overview.png").read_bytes(),
            )

    def test_draft_contains_36_unique_licensed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asset_dir = root / "assets" / "candidate"
            review_sheet = root / "review" / "overview.png"
            dataset = root / "tasks.jsonl"
            generated = generate_assets(
                asset_dir,
                review_sheet=review_sheet,
            )
            rows = build_tasks(
                " candidate-robustness-v0 ",
                "assets/candidate",
            )
            write_jsonl(dataset, rows)
            tasks = load_tasks(dataset, media_root=root)

        self.assertEqual(len(generated), 13)
        self.assertEqual(len(SCENES), 12)
        self.assertEqual(len(tasks), 36)
        self.assertEqual(len({task.id for task in tasks}), 36)
        self.assertEqual(len({task.media[0] for task in tasks}), 12)
        self.assertEqual(
            Counter(str(task.metadata["robustness_factor"]) for task in tasks),
            {
                "small-object": 9,
                "low-contrast": 9,
                "visual-clutter": 9,
                "partial-occlusion": 9,
            },
        )
        self.assertEqual(
            Counter(str(task.metadata["category"]) for task in tasks),
            {
                "attribute-recognition": 24,
                "spatial-reasoning": 6,
                "counting": 3,
                "occlusion-reasoning": 3,
            },
        )
        self.assertEqual(
            Counter(task.scoring.type for task in tasks),
            {"normalized_exact_match": 32, "numeric_tolerance": 4},
        )
        for task in tasks:
            self.assertEqual(task.schema_version, "1.2")
            self.assertEqual(
                task.metadata["dataset_version"],
                "candidate-robustness-v0",
            )
            self.assertEqual(task.metadata["source"], "project-generated")
            self.assertEqual(task.metadata["license"], "Apache-2.0")
            self.assertEqual(
                task.metadata["generator"],
                "scripts/generate_robustness_images.py",
            )

    def test_assets_are_byte_stable_and_semantically_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first"
            second = root / "second"
            generate_assets(
                first / "assets",
                review_sheet=first / "overview.png",
            )
            generate_assets(
                second / "assets",
                review_sheet=second / "overview.png",
            )
            first_files = sorted(
                path.relative_to(first)
                for path in first.rglob("*")
                if path.is_file()
            )
            second_files = sorted(
                path.relative_to(second)
                for path in second.rglob("*")
                if path.is_file()
            )
            self.assertEqual(first_files, second_files)
            for relative in first_files:
                self.assertEqual(
                    (first / relative).read_bytes(),
                    (second / relative).read_bytes(),
                )

            width, height, small = _decode_rgb_png(
                first / "assets" / "small-red-square-left.png"
            )
            _, _, faint = _decode_rgb_png(
                first / "assets" / "low-contrast-blue-square-right.png"
            )
            _, _, clutter = _decode_rgb_png(
                first / "assets" / "clutter-purple-triangle-center.png"
            )
            _, _, occluded = _decode_rgb_png(
                first / "assets" / "occluded-red-circle-vertical.png"
            )
            sheet_width, sheet_height, _ = _decode_rgb_png(
                first / "overview.png"
            )

        self.assertEqual((width, height), (WIDTH, HEIGHT))
        self.assertEqual((sheet_width, sheet_height), (968, 970))
        self.assertEqual(_pixel(small, 45, 55), (239, 68, 68))
        self.assertEqual(_pixel(faint, 248, 120), (130, 160, 200))
        self.assertEqual(_pixel(clutter, 160, 120), (168, 85, 247))
        self.assertEqual(_pixel(occluded, 80, 120), (71, 85, 105))
        self.assertEqual(_pixel(occluded, 60, 120), (239, 68, 68))

    def test_static_review_is_complete_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            review = root / "review.json"
            rows = build_tasks(
                "candidate-robustness-v0",
                "assets/candidate",
            )
            write_jsonl(dataset, rows)
            write_review_template(
                review,
                dataset_path=dataset,
                dataset_version=" candidate-robustness-v0 ",
                tasks=rows,
            )

            incomplete = audit_human_review(dataset, review)
            value = json.loads(review.read_text(encoding="utf-8"))
            for entry in value["entries"]:
                entry["checks"] = {check: True for check in REVIEW_CHECKS}
                entry["reviewer"] = "test reviewer"
                entry["reviewed_at"] = "2026-08-02"
            review.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )
            complete = audit_human_review(dataset, review)
            self.assertEqual(
                value["dataset_version"],
                "candidate-robustness-v0",
            )
            value["review_media_order"] = list(
                reversed(value["review_media_order"])
            )
            review.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )
            reordered = audit_human_review(dataset, review)

        self.assertEqual(len(incomplete), 36)
        self.assertEqual(complete, [])
        self.assertIn(
            "review review_media_order does not match the dataset",
            reordered,
        )

    def test_unknown_review_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            review = root / "review.json"
            rows = build_tasks(
                "candidate-robustness-v0",
                "assets/candidate",
            )
            write_jsonl(dataset, rows)
            write_review_template(
                review,
                dataset_path=dataset,
                dataset_version="candidate-robustness-v0",
                tasks=rows,
            )
            value = json.loads(review.read_text(encoding="utf-8"))
            value["review_profile"] = "unknown-profile"
            review.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )

            findings = audit_human_review(dataset, review)

        self.assertIn(
            "review schema_version/profile combination is unsupported",
            findings,
        )

    def test_public_name_and_media_prefix_are_never_inferred(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset_version"):
            build_tasks("", "assets/candidate")
        with self.assertRaisesRegex(ValueError, "relative and portable"):
            build_tasks(
                "candidate-robustness-v0",
                "C:" + "\\private\\candidate",
            )
        with self.assertRaisesRegex(ValueError, "relative and portable"):
            build_tasks(
                "candidate-robustness-v0",
                "assets/../private",
            )


if __name__ == "__main__":
    unittest.main()

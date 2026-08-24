from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
CANONICAL_DATASET = PROJECT_ROOT / "examples/tasks/synthetic-video-v1.jsonl"
CANONICAL_ASSETS = PROJECT_ROOT / "examples/assets/synthetic-video-v1"
CANONICAL_REVIEW = PROJECT_ROOT / "docs/reviews/synthetic-video-v1.json"
CANONICAL_REVIEW_SHEETS = PROJECT_ROOT / "docs/reviews/synthetic-video-v1"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from generate_synthetic_videos import (  # noqa: E402
    CLIPS,
    FPS,
    FRAME_COUNT,
    HEIGHT,
    REVIEW_CHECKS,
    WIDTH,
    build_tasks,
    generate_assets,
    write_avi,
    write_jsonl,
    write_review_template,
)
from validate_human_review import audit_human_review  # noqa: E402

from openmultimodal_lab.datasets import load_tasks  # noqa: E402


class VideoCorpusToolingTests(unittest.TestCase):
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
                "synthetic-video-v1",
                "examples/assets/synthetic-video-v1",
            ),
        )
        self.assertEqual(len(tasks), 24)
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
            generate_assets(root / "assets", review_dir=root / "review")
            for path in CANONICAL_ASSETS.iterdir():
                self.assertEqual(
                    path.read_bytes(),
                    (root / "assets" / path.name).read_bytes(),
                )
            for path in CANONICAL_REVIEW_SHEETS.iterdir():
                self.assertEqual(
                    path.read_bytes(),
                    (root / "review" / path.name).read_bytes(),
                )

    def test_draft_contains_24_licensed_reviewable_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asset_dir = root / "assets" / "candidate"
            review_dir = root / "review-sheets"
            dataset = root / "tasks.jsonl"
            generated = generate_assets(asset_dir, review_dir=review_dir)
            rows = build_tasks("candidate-video-v0", "assets/candidate")
            write_jsonl(dataset, rows)

            tasks = load_tasks(dataset, media_root=root)

        self.assertEqual(len(generated), 16)
        self.assertEqual(len(tasks), 24)
        self.assertEqual(len({task.id for task in tasks}), 24)
        self.assertEqual(
            Counter(str(task.metadata["category"]) for task in tasks),
            {
                "motion-direction": 4,
                "temporal-position": 8,
                "event-order": 4,
                "temporal-counting": 5,
                "state-change": 3,
            },
        )
        self.assertEqual(
            Counter(task.scoring.type for task in tasks),
            {"normalized_exact_match": 19, "numeric_tolerance": 5},
        )
        for task in tasks:
            self.assertEqual(task.schema_version, "1.2")
            self.assertEqual(
                task.metadata["dataset_version"],
                "candidate-video-v0",
            )
            self.assertEqual(task.metadata["source"], "project-generated")
            self.assertEqual(task.metadata["license"], "Apache-2.0")
            self.assertEqual(
                task.metadata["generator"],
                "scripts/generate_synthetic_videos.py",
            )
            self.assertEqual(len(task.media), 1)
            self.assertTrue(task.media[0].endswith(".avi"))

    def test_assets_are_byte_stable_and_avi_headers_are_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first"
            second = root / "second"
            generate_assets(first / "assets", review_dir=first / "review")
            generate_assets(second / "assets", review_dir=second / "review")

            first_files = sorted(
                path.relative_to(first) for path in first.rglob("*") if path.is_file()
            )
            second_files = sorted(
                path.relative_to(second)
                for path in second.rglob("*")
                if path.is_file()
            )
            sample = (first / "assets" / "motion-right-red-square.avi").read_bytes()

            self.assertEqual(first_files, second_files)
            for relative in first_files:
                self.assertEqual(
                    (first / relative).read_bytes(),
                    (second / relative).read_bytes(),
                )

        self.assertEqual(sample[:4], b"RIFF")
        self.assertEqual(sample[8:12], b"AVI ")
        self.assertEqual(struct.unpack_from("<I", sample, 4)[0], len(sample) - 8)
        main_header = sample.index(b"avih") + 8
        self.assertEqual(
            struct.unpack_from("<I", sample, main_header + 16)[0],
            FRAME_COUNT,
        )
        self.assertEqual(
            struct.unpack_from("<I", sample, main_header + 32)[0],
            WIDTH,
        )
        self.assertEqual(
            struct.unpack_from("<I", sample, main_header + 36)[0],
            HEIGHT,
        )

    @unittest.skipUnless(
        importlib.util.find_spec("av") is not None,
        "PyAV is an optional real-model dependency",
    )
    def test_pyav_decodes_every_generated_frame(self) -> None:
        import av
        import numpy as np

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            right_video = root / "right.avi"
            down_video = root / "down.avi"
            write_avi(right_video, CLIPS[0].renderer())
            write_avi(down_video, CLIPS[2].renderer())

            def decode(path: Path) -> tuple[tuple[int, int, object], list[object]]:
                with av.open(str(path)) as container:
                    stream = container.streams.video[0]
                    metadata = (stream.width, stream.height, stream.average_rate)
                    frames = [
                        frame.to_ndarray(format="rgb24")
                        for frame in container.decode(video=0)
                    ]
                return metadata, frames

            stream_metadata, right_frames = decode(right_video)
            _, down_frames = decode(down_video)

        def red_x(frame: object) -> float:
            mask = (
                (frame[:, :, 0] > 200)
                & (frame[:, :, 1] < 100)
                & (frame[:, :, 2] < 100)
            )
            return float(np.where(mask)[1].mean())

        def green_y(frame: object) -> float:
            mask = (
                (frame[:, :, 0] < 100)
                & (frame[:, :, 1] > 120)
                & (frame[:, :, 2] < 150)
            )
            return float(np.where(mask)[0].mean())

        self.assertEqual(len(right_frames), FRAME_COUNT)
        self.assertEqual(len(down_frames), FRAME_COUNT)
        width, height, average_rate = stream_metadata
        self.assertEqual(width, WIDTH)
        self.assertEqual(height, HEIGHT)
        self.assertEqual(float(average_rate), float(FPS))
        self.assertLess(red_x(right_frames[0]), red_x(right_frames[-1]))
        self.assertLess(green_y(down_frames[0]), green_y(down_frames[-1]))

    def test_review_must_be_complete_and_bound_to_dataset_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            review = root / "review.json"
            rows = build_tasks("candidate-video-v0", "assets/candidate")
            write_jsonl(dataset, rows)
            write_review_template(
                review,
                dataset_path=dataset,
                dataset_version="candidate-video-v0",
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
            dataset.write_text(
                dataset.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            stale = audit_human_review(dataset, review)

        self.assertTrue(incomplete)
        self.assertTrue(
            any("checks not approved" in finding for finding in incomplete)
        )
        self.assertEqual(complete, [])
        self.assertIn(
            "review dataset_sha256 does not match the dataset",
            stale,
        )

    def test_public_name_and_media_prefix_are_never_inferred(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset_version"):
            build_tasks("", "assets/candidate")
        with self.assertRaisesRegex(ValueError, "relative and portable"):
            build_tasks(
                "candidate-video-v0",
                "C:" + "\\private\\candidate",
            )
        with self.assertRaisesRegex(ValueError, "relative and portable"):
            build_tasks("candidate-video-v0", "assets/../private")

    def test_review_date_requires_canonical_iso_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            review = root / "review.json"
            rows = build_tasks("candidate-video-v0", "assets/candidate")
            write_jsonl(dataset, rows)
            write_review_template(
                review,
                dataset_path=dataset,
                dataset_version="candidate-video-v0",
                tasks=rows,
            )
            value = json.loads(review.read_text(encoding="utf-8"))
            for entry in value["entries"]:
                entry["checks"] = {check: True for check in REVIEW_CHECKS}
                entry["reviewer"] = "test reviewer"
                entry["reviewed_at"] = "20260802"
            review.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )

            findings = audit_human_review(dataset, review)

        self.assertEqual(len(findings), 24)
        self.assertTrue(
            all("reviewed_at is not YYYY-MM-DD" in item for item in findings)
        )

    def test_review_parser_rejects_oversized_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            review = root / "review.json"
            write_jsonl(
                dataset,
                build_tasks("candidate-video-v0", "assets/candidate"),
            )
            review.write_text("{}\n", encoding="utf-8")

            with patch("validate_human_review.MAX_REVIEW_BYTES", 2):
                findings = audit_human_review(dataset, review)

        self.assertEqual(
            findings,
            ["review record is unreadable: ValueError"],
        )


if __name__ == "__main__":
    unittest.main()

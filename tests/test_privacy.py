from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openmultimodal_lab.adapters.errors import AdapterInputError
from openmultimodal_lab.models import EvaluationTask
from openmultimodal_lab.privacy import (
    portable_media_references,
    portable_path_reference,
    redact_local_paths,
)
from openmultimodal_lab.runner import run_benchmark


class PrivacyTests(unittest.TestCase):
    def test_portable_media_references_remove_absolute_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            absolute = Path(temp_dir) / "private-image.png"

            references = portable_media_references(
                ("examples/public.png", str(absolute))
            )

        self.assertEqual(
            references,
            ("examples/public.png", "private-image.png"),
        )

    def test_redacts_common_local_paths(self) -> None:
        windows_path = "C:" + "\\Users\\student\\cache\\model.bin"
        posix_path = "/" + "home/student/.cache/model.bin"
        posix_system_path = "/" + "opt/private/cache.bin"
        unc_path = "\\\\" + "server\\private\\cache.bin"
        message = (
            f"failed at {windows_path}, {posix_path}, {posix_system_path}, "
            f"and {unc_path}"
        )

        redacted = redact_local_paths(message)

        self.assertNotIn("student", redacted)
        self.assertNotIn("C:" + "\\", redacted)
        self.assertIn("<local-path>", redacted)
        self.assertIn("<home-path>", redacted)

    def test_portable_path_reference_is_cross_platform(self) -> None:
        windows_path = "C:" + "\\private\\dataset.jsonl"
        posix_path = "/" + "srv/private/results.jsonl"
        unc_path = "\\\\" + "server\\share\\video.mp4"

        self.assertEqual(
            portable_path_reference(windows_path),
            "dataset.jsonl",
        )
        self.assertEqual(
            portable_path_reference(posix_path),
            "results.jsonl",
        )
        self.assertEqual(portable_path_reference(unc_path), "video.mp4")
        self.assertEqual(
            portable_path_reference("runs/result.jsonl"),
            "runs/result.jsonl",
        )

    def test_run_record_redacts_absolute_media_and_error_paths(self) -> None:
        class FailingAdapter:
            name = "failing"
            revision = "test"

            @staticmethod
            def generate(task: EvaluationTask) -> None:
                raise AdapterInputError(
                    f"could not read {task.media[0]}"
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            private_media = root / "private.png"
            task = EvaluationTask(
                id="private-media",
                prompt="Describe.",
                media=(str(private_media),),
            )
            output = root / "run.jsonl"

            records = run_benchmark([task], FailingAdapter(), output)
            serialized = output.read_text(encoding="utf-8")

        self.assertEqual(records[0].media, ("private.png",))
        self.assertNotIn(str(root), records[0].error or "")
        self.assertNotIn(str(root), serialized)


if __name__ == "__main__":
    unittest.main()

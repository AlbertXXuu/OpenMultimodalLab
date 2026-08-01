from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openmultimodal_lab.manifest import (
    ManifestResumeError,
    _git_state,
    _package_versions,
    build_run_manifest,
    checkpoint_run_manifest,
    finalize_run_manifest,
    load_run_manifest,
    manifest_path_for,
    prepare_resumed_manifest,
    validate_resume_manifest,
    validate_resume_record_count,
    write_run_manifest,
)
from openmultimodal_lab.models import EvaluationTask


class RunManifestTests(unittest.TestCase):
    def test_git_state_excludes_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "runs" / "result.jsonl"
            manifest = manifest_path_for(output)
            responses = [
                SimpleNamespace(stdout="abc123\n"),
                SimpleNamespace(stdout=""),
            ]
            with patch(
                "openmultimodal_lab.manifest.subprocess.run",
                side_effect=responses,
            ) as run:
                state = _git_state(root, (output, manifest))

        status_arguments = run.call_args_list[1].args[0]
        self.assertEqual(state, {"commit": "abc123", "dirty": False})
        self.assertIn(":(exclude)runs/result.jsonl", status_arguments)
        self.assertIn(
            ":(exclude)runs/result.jsonl.manifest.json",
            status_arguments,
        )

    def test_runtime_inventory_includes_model_loading_dependencies(self) -> None:
        with patch(
            "openmultimodal_lab.manifest.importlib.metadata.version",
            return_value="test-version",
        ) as version:
            packages = _package_versions()

        queried = {call.args[0] for call in version.call_args_list}
        self.assertIn("av", queried)
        self.assertIn("huggingface-hub", queried)
        self.assertIn("num2words", queried)
        self.assertIn("safetensors", queried)
        self.assertIn("tokenizers", queried)
        self.assertEqual(packages["num2words"], "test-version")

    def test_manifest_hashes_inputs_without_absolute_path_leaks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            dataset.write_text('{"id":"task-1"}\n', encoding="utf-8")
            media = root / "image.png"
            media.write_bytes(b"image")
            output = root / "runs" / "result.jsonl"
            task = EvaluationTask(
                id="task-1",
                prompt="Describe.",
                media=("image.png",),
                metadata={"dataset_version": "test-v1"},
            )

            manifest = build_run_manifest(
                dataset_path=dataset,
                output_path=output,
                media_root=root,
                tasks=[task],
                backend="mock",
                model_id="mock",
                model_revision="deterministic-v1",
                max_new_tokens=32,
                warmup=1,
                repetitions=3,
                categories=["image-description"],
                gpu_summary="not detected",
                project_root=root,
            )
            serialized = json.dumps(manifest)

        self.assertEqual(manifest["dataset"]["path"], "tasks.jsonl")
        self.assertEqual(manifest["output"]["path"], "runs/result.jsonl")
        self.assertEqual(manifest["dataset"]["versions"], ["test-v1"])
        self.assertEqual(len(manifest["dataset"]["sha256"]), 64)
        self.assertEqual(len(manifest["dataset"]["media"][0]["sha256"]), 64)
        self.assertNotIn(temp_dir, serialized)
        self.assertEqual(manifest["protocol"]["warmup_attempts"], 1)
        self.assertEqual(manifest["protocol"]["repetitions"], 3)
        self.assertEqual(manifest["protocol"]["max_retries"], 0)
        self.assertIsNone(manifest["protocol"]["attempt_timeout_seconds"])

    def test_video_sampling_configuration_is_explicit_when_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "video-tasks.jsonl"
            dataset.write_text('{"id":"video-1"}\n', encoding="utf-8")
            video = root / "clip.mp4"
            video.write_bytes(b"video")
            task = EvaluationTask(
                id="video-1",
                prompt="What changes?",
                media=("clip.mp4",),
                metadata={"dataset_version": "test-video"},
            )

            manifest = build_run_manifest(
                dataset_path=dataset,
                output_path=root / "result.jsonl",
                media_root=root,
                tasks=[task],
                backend="qwen3-vl",
                model_id="model",
                model_revision="revision",
                max_new_tokens=32,
                warmup=1,
                repetitions=3,
                categories=[],
                gpu_summary="test gpu",
                project_root=root,
                video_num_frames=8,
            )

        self.assertEqual(manifest["generation"]["video_num_frames"], 8)

    def test_manifest_path_and_atomic_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.jsonl"
            path = manifest_path_for(output)
            manifest = finalize_run_manifest(
                {"schema_version": "1.0", "status": "started"},
                [],
                status="completed",
            )

            with patch(
                "openmultimodal_lab.manifest.os.fsync",
            ) as fsync:
                write_run_manifest(path, manifest)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(path.name, "result.jsonl.manifest.json")
        self.assertEqual(loaded["status"], "completed")
        self.assertEqual(loaded["records_written"], 0)
        self.assertGreaterEqual(fsync.call_count, 1)

    def test_final_manifest_hashes_the_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.jsonl"
            output.write_text('{"record": 1}\n', encoding="utf-8")
            expected_size = output.stat().st_size

            manifest = finalize_run_manifest(
                {
                    "schema_version": "1.0",
                    "status": "started",
                    "output": {"path": "result.jsonl"},
                },
                [],
                status="failed",
                output_path=output,
            )
            checkpoint = checkpoint_run_manifest(
                {
                    "schema_version": "1.0",
                    "status": "started",
                    "output": {"path": "result.jsonl"},
                },
                [],
                output_path=output,
            )

        self.assertEqual(manifest["output"]["size_bytes"], expected_size)
        self.assertEqual(len(manifest["output"]["sha256"]), 64)
        self.assertEqual(checkpoint["status"], "started")
        self.assertEqual(checkpoint["records_written"], 0)
        self.assertEqual(
            checkpoint["output"]["sha256"],
            manifest["output"]["sha256"],
        )

    def test_resume_manifest_checks_integrity_and_prepares_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dataset = root / "tasks.jsonl"
            dataset.write_text('{"id":"task-1"}\n', encoding="utf-8")
            output = root / "result.jsonl"
            output.write_text('{"record": 1}\n', encoding="utf-8")
            task = EvaluationTask(id="task-1", prompt="Describe.")
            arguments = {
                "dataset_path": dataset,
                "output_path": output,
                "media_root": root,
                "tasks": [task],
                "backend": "mock",
                "model_id": "mock",
                "model_revision": "deterministic-v1",
                "max_new_tokens": 32,
                "warmup": 0,
                "repetitions": 1,
                "categories": [],
                "gpu_summary": "not detected",
                "project_root": root,
            }
            candidate = build_run_manifest(**arguments)
            existing = finalize_run_manifest(
                candidate,
                [],
                status="failed",
                error="KeyboardInterrupt",
                output_path=output,
            )

            validate_resume_manifest(
                existing,
                build_run_manifest(**arguments),
                output_path=output,
            )
            validate_resume_record_count(existing, 0)
            resumed = prepare_resumed_manifest(existing)

            changed_retry_policy = dict(arguments)
            changed_retry_policy["max_retries"] = 1
            with self.assertRaisesRegex(
                ManifestResumeError,
                "protocol",
            ):
                validate_resume_manifest(
                    existing,
                    build_run_manifest(**changed_retry_policy),
                    output_path=output,
                )

            invalid_values = (
                ("output.sha256", {"output": {"sha256": "not-a-hash"}}),
                ("output.size_bytes", {"output": {"size_bytes": True}}),
                ("records_written", {"records_written": None}),
                ("resume_count", {"resume_count": "one"}),
            )
            for expected_error, replacement in invalid_values:
                with self.subTest(field=expected_error):
                    invalid = json.loads(json.dumps(existing))
                    if "output" in replacement:
                        invalid["output"].update(replacement["output"])
                    else:
                        invalid.update(replacement)
                    with self.assertRaisesRegex(
                        ManifestResumeError,
                        expected_error,
                    ):
                        if expected_error.startswith("output."):
                            validate_resume_manifest(
                                invalid,
                                build_run_manifest(**arguments),
                                output_path=output,
                            )
                        elif expected_error == "records_written":
                            validate_resume_record_count(invalid, 0)
                        else:
                            prepare_resumed_manifest(invalid)

            output.write_text('{"record": 2}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                ManifestResumeError,
                "SHA-256",
            ):
                validate_resume_manifest(
                    existing,
                    build_run_manifest(**arguments),
                    output_path=output,
                )
            with self.assertRaisesRegex(
                ManifestResumeError,
                "record count",
            ):
                validate_resume_record_count(existing, 1)

        self.assertEqual(resumed["status"], "started")
        self.assertEqual(resumed["resume_count"], 1)
        self.assertIn("resumed_at_utc", resumed)
        self.assertNotIn("completed_at_utc", resumed)
        self.assertEqual(
            resumed["output"]["sha256"],
            existing["output"]["sha256"],
        )
        self.assertEqual(
            resumed["output"]["size_bytes"],
            existing["output"]["size_bytes"],
        )

    def test_manifest_loader_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.manifest.json"
            with self.assertRaisesRegex(
                ManifestResumeError,
                "manifest does not exist",
            ):
                load_run_manifest(missing)


if __name__ == "__main__":
    unittest.main()

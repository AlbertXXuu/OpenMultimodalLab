from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openmultimodal_lab.manifest import (
    _package_versions,
    build_run_manifest,
    finalize_run_manifest,
    manifest_path_for,
    write_run_manifest,
)
from openmultimodal_lab.models import EvaluationTask


class RunManifestTests(unittest.TestCase):
    def test_runtime_inventory_includes_model_loading_dependencies(self) -> None:
        with patch(
            "openmultimodal_lab.manifest.importlib.metadata.version",
            return_value="test-version",
        ) as version:
            packages = _package_versions()

        queried = {call.args[0] for call in version.call_args_list}
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

    def test_manifest_path_and_atomic_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.jsonl"
            path = manifest_path_for(output)
            manifest = finalize_run_manifest(
                {"schema_version": "1.0", "status": "started"},
                [],
                status="completed",
            )

            write_run_manifest(path, manifest)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(path.name, "result.jsonl.manifest.json")
        self.assertEqual(loaded["status"], "completed")
        self.assertEqual(loaded["records_written"], 0)


if __name__ == "__main__":
    unittest.main()

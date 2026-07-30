from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from openmultimodal_lab.reporting import load_records, summarize


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "docs" / "reports" / "results"
FORMAL_QWEN_RESULT = (
    RESULTS_ROOT / "2026-07-31-qwen3-vl-synthetic-v1-1-formal.jsonl"
)
FORMAL_QWEN_MANIFEST = (
    RESULTS_ROOT / "2026-07-31-qwen3-vl-synthetic-v1-1-formal.manifest.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class PublishedResultTests(unittest.TestCase):
    def test_formal_qwen_baseline_is_complete_and_unchanged(self) -> None:
        records = load_records(FORMAL_QWEN_RESULT)
        summary = summarize(records)
        manifest_text = FORMAL_QWEN_MANIFEST.read_text(encoding="utf-8")
        manifest = json.loads(manifest_text)

        self.assertEqual(
            _sha256(FORMAL_QWEN_RESULT),
            "AAB9967307C2DC562759A47F1DA0719AA964911C8CD1F75E70F6D42767154067",
        )
        self.assertEqual(
            _sha256(FORMAL_QWEN_MANIFEST),
            "A20E65E7ADB30987022D524D651B90EECEAAF9ED522F6038FBFD06ED591FCAED",
        )
        self.assertEqual(summary["total_records"], 31)
        self.assertEqual(summary["warmup_attempts"], 1)
        self.assertEqual(summary["total_tasks"], 30)
        self.assertEqual(summary["repetitions"], 3)
        self.assertTrue(summary["formal_performance_run"])
        self.assertEqual(summary["successful_tasks"], 30)
        self.assertEqual(summary["mean_score"], 1.0)
        self.assertEqual(summary["failures"], {})
        self.assertAlmostEqual(summary["median_ttft_ms"], 114.3966)
        self.assertAlmostEqual(summary["peak_gpu_memory_mb"], 4093.28515625)

        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["records_written"], 31)
        self.assertEqual(manifest["measurement_records"], 30)
        self.assertFalse(manifest["environment"]["git"]["dirty"])
        self.assertEqual(
            manifest["environment"]["git"]["commit"],
            "92c2ae7f58eaf36de7c3e2833a1ce191be3b284e",
        )
        self.assertNotIn("albertxu", manifest_text.casefold())
        self.assertNotIn("C:\\", manifest_text)
        self.assertNotIn("D:\\", manifest_text)

    def test_formal_manifest_hashes_current_dataset_and_media(self) -> None:
        manifest = json.loads(FORMAL_QWEN_MANIFEST.read_text(encoding="utf-8"))
        dataset = manifest["dataset"]
        dataset_path = PROJECT_ROOT / dataset["path"]

        self.assertEqual(
            hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            dataset["sha256"],
        )
        for media in dataset["media"]:
            media_path = PROJECT_ROOT / media["path"]
            self.assertEqual(
                hashlib.sha256(media_path.read_bytes()).hexdigest(),
                media["sha256"],
            )


if __name__ == "__main__":
    unittest.main()

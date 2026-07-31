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
COMPARISON_QWEN_RESULT = (
    RESULTS_ROOT / "2026-07-31-qwen3-vl-comparison-formal.jsonl"
)
COMPARISON_QWEN_MANIFEST = (
    RESULTS_ROOT / "2026-07-31-qwen3-vl-comparison-formal.manifest.json"
)
COMPARISON_SMOL_RESULT = (
    RESULTS_ROOT / "2026-07-31-smolvlm2-500m-comparison-formal.jsonl"
)
COMPARISON_SMOL_MANIFEST = (
    RESULTS_ROOT / "2026-07-31-smolvlm2-500m-comparison-formal.manifest.json"
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
        self.assertNotRegex(manifest_text, r"(?i)[a-z]:[\\/]")
        self.assertNotRegex(
            manifest_text,
            r"(?i)/(?:home|users)/[^/\s]+/",
        )

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

    def test_two_model_comparison_is_complete_and_unchanged(self) -> None:
        cases = (
            {
                "result": COMPARISON_QWEN_RESULT,
                "manifest": COMPARISON_QWEN_MANIFEST,
                "result_sha256": (
                    "BB3CD773A66B85713D221E632CE44D0D"
                    "561950D6EDE4CE9C8BB0CCACFD7E10FF"
                ),
                "manifest_sha256": (
                    "FE4F4CE01102CF572A61AD11C102D332"
                    "609D8A374D6420D11D3205F05FFE5B0A"
                ),
                "backend": "qwen3-vl",
                "mean_score": 1.0,
                "median_latency_ms": 182.7798,
                "median_ttft_ms": 107.37045,
                "peak_gpu_memory_mb": 4093.28515625,
            },
            {
                "result": COMPARISON_SMOL_RESULT,
                "manifest": COMPARISON_SMOL_MANIFEST,
                "result_sha256": (
                    "841002994BE8F733BAB0CC9CA4E5627B"
                    "4E0198145A84871BD1B61427086625BA"
                ),
                "manifest_sha256": (
                    "E367C63C7547FC398AB7C0A3196C17E"
                    "FB699E56F0C57BA1BA12469A0B45E28A8"
                ),
                "backend": "smolvlm2",
                "mean_score": 0.7333333333333333,
                "median_latency_ms": 386.7335,
                "median_ttft_ms": 257.63975,
                "peak_gpu_memory_mb": 1265.279296875,
            },
        )

        for case in cases:
            with self.subTest(backend=case["backend"]):
                records = load_records(case["result"])
                summary = summarize(records)
                manifest_text = case["manifest"].read_text(encoding="utf-8")
                manifest = json.loads(manifest_text)

                self.assertEqual(_sha256(case["result"]), case["result_sha256"])
                self.assertEqual(
                    _sha256(case["manifest"]),
                    case["manifest_sha256"],
                )
                self.assertEqual(summary["total_records"], 31)
                self.assertEqual(summary["warmup_attempts"], 1)
                self.assertEqual(summary["total_tasks"], 30)
                self.assertEqual(summary["unique_tasks"], 10)
                self.assertEqual(summary["repetitions"], 3)
                self.assertTrue(summary["formal_performance_run"])
                self.assertEqual(summary["successful_tasks"], 30)
                self.assertEqual(summary["failures"], {})
                self.assertAlmostEqual(
                    summary["mean_score"],
                    case["mean_score"],
                )
                self.assertAlmostEqual(
                    summary["median_latency_ms"],
                    case["median_latency_ms"],
                )
                self.assertAlmostEqual(
                    summary["median_ttft_ms"],
                    case["median_ttft_ms"],
                )
                self.assertAlmostEqual(
                    summary["peak_gpu_memory_mb"],
                    case["peak_gpu_memory_mb"],
                )

                self.assertEqual(manifest["backend"]["name"], case["backend"])
                self.assertEqual(manifest["status"], "completed")
                self.assertEqual(manifest["records_written"], 31)
                self.assertEqual(manifest["measurement_records"], 30)
                self.assertFalse(manifest["environment"]["git"]["dirty"])
                self.assertEqual(
                    manifest["environment"]["git"]["commit"],
                    "e6d25410e66c483747a519b1877f0ae4a1d5b380",
                )
                self.assertEqual(
                    manifest["environment"]["packages"]["num2words"],
                    "0.5.14",
                )
                self.assertIn(
                    "huggingface-hub",
                    manifest["environment"]["packages"],
                )
                self.assertNotRegex(manifest_text, r"(?i)[a-z]:[\\/]")
                self.assertNotRegex(
                    manifest_text,
                    r"(?i)/(?:home|users)/[^/\s]+/",
                )

    def test_two_model_manifests_share_current_dataset_and_media(self) -> None:
        manifests = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in (COMPARISON_QWEN_MANIFEST, COMPARISON_SMOL_MANIFEST)
        ]
        reference_dataset = manifests[0]["dataset"]

        self.assertEqual(manifests[1]["dataset"], reference_dataset)
        self.assertEqual(len(reference_dataset["task_ids"]), 10)

        dataset_path = PROJECT_ROOT / reference_dataset["path"]
        self.assertEqual(
            hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            reference_dataset["sha256"],
        )
        for media in reference_dataset["media"]:
            media_path = PROJECT_ROOT / media["path"]
            self.assertEqual(
                hashlib.sha256(media_path.read_bytes()).hexdigest(),
                media["sha256"],
            )


if __name__ == "__main__":
    unittest.main()

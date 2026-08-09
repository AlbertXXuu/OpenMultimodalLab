from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT_ROOT / "docs" / "reports" / "results"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SecurityEvidenceTests(unittest.TestCase):
    def test_final_source_and_runtime_audits_match_the_review(self) -> None:
        bandit_path = RESULTS / "final-bandit-security-audit.json"
        runtime_path = RESULTS / "final-runtime-vulnerability-audit.json"
        review = (
            PROJECT_ROOT / "docs" / "reports" / "final-security-review.md"
        ).read_text(encoding="utf-8")
        bandit = json.loads(bandit_path.read_text(encoding="utf-8"))
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))

        self.assertEqual(len(bandit["results"]), 8)
        self.assertEqual(
            {item["issue_severity"] for item in bandit["results"]},
            {"LOW"},
        )
        self.assertEqual(
            {item["test_id"] for item in bandit["results"]},
            {"B404", "B603", "B607"},
        )
        audited = [item for item in runtime["dependencies"] if "vulns" in item]
        skipped = [
            item for item in runtime["dependencies"] if "skip_reason" in item
        ]
        self.assertEqual(len(audited), 41)
        self.assertFalse(any(item["vulns"] for item in audited))
        self.assertEqual(
            {item["name"] for item in skipped},
            {"openmultimodal-lab", "torch", "torchvision"},
        )
        self.assertIn(_sha256(bandit_path), review)
        self.assertIn(_sha256(runtime_path), review)

    def test_runtime_code_does_not_use_optimization_removed_asserts(self) -> None:
        for root in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
            for path in root.rglob("*.py"):
                with self.subTest(path=path.relative_to(PROJECT_ROOT)):
                    self.assertNotIn(
                        "assert ",
                        path.read_text(encoding="utf-8"),
                    )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from build_formal_input import (  # noqa: E402
    FormalInputError,
    build_formal_input,
)


CANONICAL_CONFIG = PROJECT_ROOT / "configs" / "formal-evaluation.json"
COMMITTED_INPUT = PROJECT_ROOT / "runs" / "formal-evaluation-input.jsonl"
EXPECTED_HASH = "d18e6dce941cfac1fee0d637449229d786d7d6b601c063c0af2266b7e2d7a5a8"


class FormalInputTests(unittest.TestCase):
    def test_canonical_input_is_complete_and_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "formal-input.jsonl"
            summary = build_formal_input(CANONICAL_CONFIG, output)

            self.assertEqual(summary.task_count, 102)
            self.assertEqual(summary.sha256, EXPECTED_HASH)
            self.assertEqual(output.read_bytes().count(b"\n"), 102)
            self.assertNotIn(b"\r", output.read_bytes())
            self.assertEqual(output.read_bytes(), COMMITTED_INPUT.read_bytes())
            verified = build_formal_input(
                CANONICAL_CONFIG,
                output,
                verify_only=True,
            )

        self.assertEqual(verified.sha256, EXPECTED_HASH)

    def test_verify_rejects_tampered_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "formal-input.jsonl"
            build_formal_input(CANONICAL_CONFIG, output)
            output.write_bytes(output.read_bytes() + b"\n")

            with self.assertRaisesRegex(FormalInputError, "does not match"):
                build_formal_input(
                    CANONICAL_CONFIG,
                    output,
                    verify_only=True,
                )

    def test_rejects_stale_source_hash(self) -> None:
        config = json.loads(CANONICAL_CONFIG.read_text(encoding="utf-8"))
        config["sources"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            output = Path(temp_dir) / "formal-input.jsonl"
            config_path.write_text(
                json.dumps(config) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(FormalInputError, "SHA-256 mismatch"):
                build_formal_input(config_path, output)

    def test_rejects_source_path_traversal(self) -> None:
        config = json.loads(CANONICAL_CONFIG.read_text(encoding="utf-8"))
        config["sources"][0]["path"] = "../outside.jsonl"
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            output = Path(temp_dir) / "formal-input.jsonl"
            config_path.write_text(
                json.dumps(config) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaisesRegex(FormalInputError, "repository-relative"):
                build_formal_input(config_path, output)

    def test_rejects_output_that_overlaps_a_source(self) -> None:
        source = PROJECT_ROOT / "examples" / "tasks" / "synthetic-v1.1.jsonl"
        original = source.read_bytes()

        with self.assertRaisesRegex(FormalInputError, "overlaps"):
            build_formal_input(CANONICAL_CONFIG, source)

        self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

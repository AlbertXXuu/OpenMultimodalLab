from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKER = PROJECT_ROOT / "scripts" / "check_repository.py"


class RepositoryCheckTests(unittest.TestCase):
    def _run_checker(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CHECKER),
                "--root",
                str(root),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_valid_text_json_and_local_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs = root / "docs"
            docs.mkdir()
            (docs / "guide.md").write_text(
                "# Guide\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "[Guide](docs/guide.md)\n",
                encoding="utf-8",
            )
            (root / "config.json").write_text(
                '{"valid": true}\n',
                encoding="utf-8",
            )
            (root / "records.jsonl").write_text(
                '{"id": 1}\n{"id": 2}\n',
                encoding="utf-8",
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "safe.yml").write_text(
                "steps:\n"
                "  - uses: actions/checkout@"
                "d23441a48e516b6c34aea4fa41551a30e30af803 # v6\n",
                encoding="utf-8",
            )

            result = self._run_checker(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Repository checks passed", result.stdout)
        self.assertIn("1 Markdown links", result.stdout)
        self.assertIn("3 JSON/JSONL documents", result.stdout)

    def test_reports_broken_link_private_path_and_invalid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text(
                "[Missing](docs/missing.md)\n",
                encoding="utf-8",
            )
            (root / "notes.txt").write_text(
                "Private file: "
                + "C:"
                + "\\Users\\example\\secret.txt\n",
                encoding="utf-8",
            )
            (root / "records.jsonl").write_text(
                '{"valid": true}\nnot-json\n',
                encoding="utf-8",
            )
            issue_forms = root / ".github" / "ISSUE_TEMPLATE"
            issue_forms.mkdir(parents=True)
            (issue_forms / "broken.yml").write_text(
                "name: Broken form\n"
                "description: Missing its body definition.\n",
                encoding="utf-8",
            )
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "unsafe.yml").write_text(
                "steps:\n"
                "  - uses: actions/checkout@v6\n",
                encoding="utf-8",
            )

            result = self._run_checker(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("broken local link", result.stderr)
        self.assertIn("possible Windows absolute path", result.stderr)
        self.assertIn("invalid JSONL", result.stderr)
        self.assertIn("requires top-level 'body'", result.stderr)
        self.assertIn("must be pinned to a full commit SHA", result.stderr)

    def test_current_repository_passes(self) -> None:
        result = self._run_checker(PROJECT_ROOT)

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

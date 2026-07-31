"""Validate repository text artifacts without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "models",
        "checkpoints",
        "runs",
    }
)
TEXT_SUFFIXES = frozenset(
    {
        ".cfg",
        ".ini",
        ".json",
        ".jsonl",
        ".md",
        ".py",
        ".svg",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
TEXT_FILENAMES = frozenset(
    {
        ".env.example",
        ".gitattributes",
        ".gitignore",
        "LICENSE",
    }
)
INLINE_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK_PATTERN = re.compile(
    r"^\[[^\]]+\]:\s*(\S+)",
    flags=re.MULTILINE,
)
SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SENSITIVE_PATTERNS = (
    (
        "Windows absolute path",
        re.compile(r"(?i)\b[a-z]:[\\/]+[^\\/\s]+"),
    ),
    (
        "POSIX user-home path",
        re.compile(r"(?i)/(?:home|users)/[^/\s]+/"),
    ),
    (
        "GitHub token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "OpenAI-style API key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "AWS access key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "private-key header",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class Issue:
    """One deterministic repository validation finding."""

    path: Path
    line: int
    message: str


@dataclass(slots=True)
class Statistics:
    """Counts reported after a successful repository check."""

    text_files: int = 0
    markdown_links: int = 0
    json_documents: int = 0


def _is_excluded(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(
        part in EXCLUDED_DIRECTORY_NAMES
        or part.startswith(".venv")
        or part.endswith(".egg-info")
        for part in relative_parts[:-1]
    )


def iter_text_files(root: Path) -> list[Path]:
    """Return the repository text artifacts covered by this check."""

    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not _is_excluded(path, root)
        and (
            path.suffix.casefold() in TEXT_SUFFIXES
            or path.name in TEXT_FILENAMES
        )
    ]


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<"):
        closing = target.find(">")
        return target[1:closing] if closing >= 0 else target
    return target.split(maxsplit=1)[0] if target else ""


def _check_markdown_links(
    path: Path,
    root: Path,
    text: str,
    statistics: Statistics,
) -> list[Issue]:
    issues: list[Issue] = []
    matches = [
        *INLINE_LINK_PATTERN.finditer(text),
        *REFERENCE_LINK_PATTERN.finditer(text),
    ]
    for match in matches:
        statistics.markdown_links += 1
        target = _link_target(match.group(1))
        if (
            not target
            or target.startswith(("#", "//"))
            or SCHEME_PATTERN.match(target)
        ):
            continue
        target_path = unquote(target.split("#", 1)[0])
        if not target_path:
            continue
        resolved = (path.parent / target_path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            issues.append(
                Issue(
                    path,
                    _line_number(text, match.start()),
                    f"local link leaves repository: {target}",
                )
            )
            continue
        if not resolved.exists():
            issues.append(
                Issue(
                    path,
                    _line_number(text, match.start()),
                    f"broken local link: {target}",
                )
            )
    return issues


def _check_json(
    path: Path,
    text: str,
    statistics: Statistics,
) -> list[Issue]:
    issues: list[Issue] = []
    if path.suffix.casefold() == ".json":
        statistics.json_documents += 1
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            issues.append(
                Issue(path, exc.lineno, f"invalid JSON: {exc.msg}")
            )
        return issues

    if path.suffix.casefold() != ".jsonl":
        return issues
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            issues.append(
                Issue(path, line_number, "empty line in JSONL artifact")
            )
            continue
        statistics.json_documents += 1
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(
                Issue(path, line_number, f"invalid JSONL: {exc.msg}")
            )
            continue
        if not isinstance(value, dict):
            issues.append(
                Issue(path, line_number, "JSONL record must be an object")
            )
    return issues


def check_repository(root: Path) -> tuple[list[Issue], Statistics]:
    """Run all repository checks and return findings plus coverage counts."""

    resolved_root = root.resolve()
    issues: list[Issue] = []
    statistics = Statistics()

    for path in iter_text_files(resolved_root):
        statistics.text_files += 1
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            issues.append(Issue(path, 1, "UTF-8 BOM is not allowed"))
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(
                Issue(
                    path,
                    raw[: exc.start].count(b"\n") + 1,
                    "file is not valid UTF-8",
                )
            )
            continue

        if text and not text.endswith("\n"):
            issues.append(Issue(path, len(text.splitlines()), "missing final newline"))
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                issues.append(
                    Issue(path, line_number, "trailing whitespace")
                )
        for label, pattern in SENSITIVE_PATTERNS:
            for match in pattern.finditer(text):
                issues.append(
                    Issue(
                        path,
                        _line_number(text, match.start()),
                        f"possible {label}",
                    )
                )
        if path.suffix.casefold() == ".md":
            issues.extend(
                _check_markdown_links(
                    path,
                    resolved_root,
                    text,
                    statistics,
                )
            )
        issues.extend(_check_json(path, text, statistics))

    return issues, statistics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to inspect (default: this script's repository).",
    )
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error(f"root is not a directory: {args.root}")

    issues, statistics = check_repository(args.root)
    if issues:
        for issue in sorted(
            issues,
            key=lambda item: (str(item.path), item.line, item.message),
        ):
            relative = issue.path.resolve().relative_to(args.root.resolve())
            print(
                f"{relative.as_posix()}:{issue.line}: {issue.message}",
                file=sys.stderr,
            )
        print(
            f"Repository checks failed with {len(issues)} issue(s).",
            file=sys.stderr,
        )
        return 1

    print(
        "Repository checks passed: "
        f"{statistics.text_files} text files, "
        f"{statistics.markdown_links} Markdown links, "
        f"{statistics.json_documents} JSON/JSONL documents."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

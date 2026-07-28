"""Command-line interface for the initial benchmark workflow."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .adapters import MockAdapter
from .datasets import DatasetError, load_tasks
from .reporting import ReportError, format_summary, load_records, summarize
from .runner import run_benchmark


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oml",
        description="Run reproducible multimodal model benchmarks.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Inspect the local core runtime.")

    run_parser = commands.add_parser("run", help="Run a JSONL task dataset.")
    run_parser.add_argument("--dataset", required=True, type=Path)
    run_parser.add_argument("--output", required=True, type=Path)
    run_parser.add_argument("--backend", choices=("mock",), default="mock")
    run_parser.add_argument(
        "--media-root",
        type=Path,
        default=Path.cwd(),
        help="Base directory for relative media paths (default: current directory).",
    )

    report_parser = commands.add_parser("report", help="Summarize raw JSONL records.")
    report_parser.add_argument("--input", required=True, type=Path)
    report_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text summary.",
    )
    return parser


def _doctor() -> int:
    python_version = platform.python_version()
    print("OpenMultimodalLab doctor")
    print(f"Package version: {__version__}")
    print(f"Python: {python_version}")
    print(f"Platform: {platform.platform()}")
    print(f"Git available: {'yes' if shutil.which('git') else 'no'}")
    print(f"Working directory: {Path.cwd()}")

    if sys.version_info < (3, 11):
        print("Status: unsupported Python; install Python 3.11 or newer.")
        return 1
    if sys.version_info >= (3, 13):
        print(
            "Note: the core works on Python 3.13+, but real ML backends target "
            "Python 3.11/3.12."
        )
    print("Status: core runtime ready.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "doctor":
        return _doctor()

    if args.command == "run":
        try:
            tasks = load_tasks(args.dataset, media_root=args.media_root)
            adapter = MockAdapter()
            records = run_benchmark(tasks, adapter, args.output)
        except DatasetError as exc:
            print(f"Dataset error: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote {len(records)} records to {args.output}")
        print(format_summary(summarize([json.loads(line) for line in args.output.read_text(encoding='utf-8').splitlines()])))
        return 0

    if args.command == "report":
        try:
            summary = summarize(load_records(args.input))
        except ReportError as exc:
            print(f"Report error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_summary(summary))
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")

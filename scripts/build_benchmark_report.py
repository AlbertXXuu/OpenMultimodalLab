"""Build or verify a deterministic report bundle from formal result JSONL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openmultimodal_lab.report_bundle import (
    build_report_bundle,
    load_comparable_sources,
    verify_report_bundle,
    write_report_bundle,
)
from openmultimodal_lab.reporting import ReportError


def _parser(project_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        type=Path,
        help="Formal result JSONL; repeat for every dataset/backend pair.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory that receives or contains the six report-bundle files.",
    )
    parser.add_argument(
        "--project-root",
        default=project_root,
        type=Path,
        help="Repository root used to resolve and verify portable paths.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify an existing bundle instead of rebuilding it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    project_root = Path(__file__).resolve().parents[1]
    args = _parser(project_root).parse_args(argv)
    try:
        if args.verify:
            if args.input:
                raise ReportError("--input cannot be combined with --verify")
            manifest = verify_report_bundle(
                args.output_dir,
                project_root=args.project_root,
            )
            print(
                "Verified report bundle: "
                f"{len(manifest['sources'])} sources, "
                f"{len(manifest['outputs'])} outputs"
            )
            return 0
        if not args.input:
            raise ReportError("Provide --input at least twice when building")
        sources = load_comparable_sources(
            args.input,
            project_root=args.project_root,
        )
        files = build_report_bundle(
            sources,
            project_root=args.project_root,
        )
        write_report_bundle(args.output_dir, files)
        print(
            f"Built report bundle from {len(sources)} formal sources: "
            f"{args.output_dir}"
        )
        return 0
    except (OSError, ReportError, ValueError) as exc:
        print(f"Report bundle error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

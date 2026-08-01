"""Command-line interface for the initial benchmark workflow."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .adapters import BACKEND_NAMES, create_adapter
from .adapters.transformers_image_text import SUPPORTED_VIDEO_SUFFIXES
from .datasets import (
    DatasetError,
    available_categories,
    filter_tasks_by_categories,
    load_tasks,
)
from .manifest import (
    ManifestResumeError,
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
from .models import RunRecord
from .reporting import ReportError, format_summary, load_records, summarize
from .runner import (
    ResumeError,
    run_benchmark,
    validate_resume_output,
)


GIBIBYTE = 1024**3
RECOMMENDED_MODEL_CACHE_FREE_GIB = {
    "qwen3-vl": 8.0,
    "smolvlm2": 4.0,
}


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return parsed


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite number above 0")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oml",
        description="Run reproducible multimodal model benchmarks.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    doctor_parser = commands.add_parser(
        "doctor",
        help="Inspect the local core or model runtime.",
    )
    doctor_parser.add_argument(
        "--backend",
        choices=("core",) + BACKEND_NAMES[1:],
        default="core",
        help="Also check optional packages required by a real backend.",
    )

    run_parser = commands.add_parser("run", help="Run a JSONL task dataset.")
    run_parser.add_argument("--dataset", required=True, type=Path)
    run_parser.add_argument("--output", required=True, type=Path)
    output_mode = run_parser.add_mutually_exclusive_group()
    output_mode.add_argument(
        "--resume",
        action="store_true",
        help="Resume a compatible started or failed run without duplicates.",
    )
    output_mode.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace an existing output and manifest.",
    )
    run_parser.add_argument("--backend", choices=BACKEND_NAMES, default="mock")
    run_parser.add_argument(
        "--model-id",
        help="Override the backend's default model repository.",
    )
    run_parser.add_argument(
        "--model-revision",
        help="Override the backend's pinned model revision.",
    )
    run_parser.add_argument(
        "--max-new-tokens",
        type=_positive_int,
        default=128,
        help="Maximum tokens generated for each task (default: 128).",
    )
    run_parser.add_argument(
        "--warmup",
        type=_non_negative_int,
        default=0,
        help="Unscored warm-up attempts on the first task (default: 0).",
    )
    run_parser.add_argument(
        "--repetitions",
        type=_positive_int,
        default=1,
        help="Measured repetitions of the selected task set (default: 1).",
    )
    run_parser.add_argument(
        "--attempt-timeout-seconds",
        type=_positive_float,
        default=None,
        help=(
            "Cooperative inference deadline per generation invocation; "
            "one-time model loading is excluded (default: disabled)."
        ),
    )
    run_parser.add_argument(
        "--max-retries",
        type=_non_negative_int,
        default=0,
        help=(
            "Retries after timeout or generation_error; every invocation is "
            "persisted (default: 0)."
        ),
    )
    run_parser.add_argument(
        "--category",
        action="append",
        default=[],
        metavar="CATEGORY",
        help="Run only an exact task category; repeat to select multiple categories.",
    )
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


def _gpu_summary() -> str:
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return "not detected"
    try:
        result = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "nvidia-smi failed"
    return result.stdout.strip() or "not detected"


def _hugging_face_cache_path() -> Path:
    explicit_hub_cache = os.environ.get("HF_HUB_CACHE")
    if explicit_hub_cache:
        return Path(explicit_hub_cache).expanduser()

    explicit_home = os.environ.get("HF_HOME")
    if explicit_home:
        return Path(explicit_home).expanduser() / "hub"

    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        return Path(xdg_cache_home).expanduser() / "huggingface" / "hub"

    return Path.home() / ".cache" / "huggingface" / "hub"


def _disk_free_gib(path: Path) -> float | None:
    candidate = path.expanduser()
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            return None
        candidate = parent
    try:
        free_bytes = shutil.disk_usage(candidate).free
    except OSError:
        return None
    return free_bytes / GIBIBYTE


def _format_free_disk(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.1f} GiB"


def _doctor(backend: str) -> int:
    python_version = platform.python_version()
    gpu_summary = _gpu_summary()
    working_disk_free = _disk_free_gib(Path.cwd())
    print("OpenMultimodalLab doctor")
    print(f"Package version: {__version__}")
    print(f"Python: {python_version}")
    print(f"Platform: {platform.platform()}")
    print(f"Git available: {'yes' if shutil.which('git') else 'no'}")
    print(f"NVIDIA GPU: {gpu_summary}")
    print(f"Working directory: {Path.cwd()}")
    print(f"Working disk free: {_format_free_disk(working_disk_free)}")

    if sys.version_info < (3, 11):
        print("Status: unsupported Python; install Python 3.11 or newer.")
        return 1
    if sys.version_info >= (3, 13):
        print(
            "Note: the core works on Python 3.13+, but real ML backends target "
            "Python 3.11/3.12."
        )
    if backend in {"qwen3-vl", "smolvlm2"}:
        backend_label = {
            "qwen3-vl": "Qwen3-VL",
            "smolvlm2": "SmolVLM2",
        }[backend]
        model_cache_free = _disk_free_gib(_hugging_face_cache_path())
        recommended_free = RECOMMENDED_MODEL_CACHE_FREE_GIB[backend]
        print(
            "Hugging Face cache disk free: "
            f"{_format_free_disk(model_cache_free)}"
        )
        if (
            model_cache_free is not None
            and model_cache_free < recommended_free
        ):
            print(
                f"Warning: {backend_label} setup recommends at least "
                f"{recommended_free:.1f} GiB free on the model-cache disk; "
                f"only {model_cache_free:.1f} GiB is available."
            )
        required_modules = (
            "av",
            "numpy",
            "torch",
            "torchvision",
            "transformers",
            "accelerate",
            "PIL",
        )
        if backend == "smolvlm2":
            required_modules += ("num2words",)
        missing = [
            module
            for module in required_modules
            if importlib.util.find_spec(module) is None
        ]
        if missing:
            print(f"Missing {backend_label} modules: {', '.join(missing)}")
            print(
                f'Install with: python -m pip install -e ".[{backend}]"'
            )
            print(f"Status: {backend_label} runtime is not ready.")
            return 1
        try:
            torch = importlib.import_module("torch")
        except (ImportError, OSError) as exc:
            print(f"Could not import PyTorch: {type(exc).__name__}: {exc}")
            print(f"Status: {backend_label} runtime is not ready.")
            return 1
        torch_version = getattr(torch, "__version__", "unknown")
        cuda_version = getattr(getattr(torch, "version", None), "cuda", None)
        cuda_available = bool(torch.cuda.is_available())
        print(f"PyTorch: {torch_version}")
        print(f"PyTorch CUDA build: {cuda_version or 'none'}")
        print(f"CUDA available to PyTorch: {'yes' if cuda_available else 'no'}")
        if gpu_summary not in {"not detected", "nvidia-smi failed"} and not cuda_available:
            print(
                "Detected an NVIDIA GPU, but PyTorch cannot use CUDA. "
                "Install a CUDA-enabled PyTorch wheel."
            )
            print(f"Status: {backend_label} GPU runtime is not ready.")
            return 1
        if backend == "smolvlm2" and cuda_available:
            is_bf16_supported = getattr(
                torch.cuda,
                "is_bf16_supported",
                None,
            )
            bf16_supported = (
                callable(is_bf16_supported)
                and bool(is_bf16_supported())
            )
            print(
                "CUDA BF16 supported: "
                f"{'yes' if bf16_supported else 'no'}"
            )
            if not bf16_supported:
                print(
                    "SmolVLM2's verified profile requires native BF16 support."
                )
                print("Status: SmolVLM2 GPU runtime is not ready.")
                return 1
        print(f"Status: {backend_label} runtime dependencies are ready.")
        return 0

    print("Status: core runtime ready.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "doctor":
        return _doctor(args.backend)

    if args.command == "run":
        try:
            tasks = load_tasks(args.dataset, media_root=args.media_root)
            if args.category:
                all_categories = available_categories(tasks)
                tasks = filter_tasks_by_categories(tasks, args.category)
                if not tasks:
                    requested = ", ".join(dict.fromkeys(args.category))
                    available = ", ".join(all_categories) or "none"
                    raise DatasetError(
                        f"No tasks matched categories: {requested}. "
                        f"Available: {available}"
                    )
            adapter = create_adapter(
                args.backend,
                media_root=args.media_root,
                model_id=args.model_id,
                revision=args.model_revision,
                max_new_tokens=args.max_new_tokens,
            )
            manifest_path = manifest_path_for(args.output)
            manifest = build_run_manifest(
                dataset_path=args.dataset,
                output_path=args.output,
                media_root=args.media_root,
                tasks=tasks,
                backend=args.backend,
                model_id=str(getattr(adapter, "model_id", args.backend)),
                model_revision=str(
                    getattr(adapter, "revision", "deterministic")
                ),
                max_new_tokens=args.max_new_tokens,
                warmup=args.warmup,
                repetitions=args.repetitions,
                max_retries=args.max_retries,
                timeout_seconds=args.attempt_timeout_seconds,
                categories=args.category,
                gpu_summary=_gpu_summary(),
                project_root=Path.cwd(),
                video_num_frames=(
                    int(adapter.video_num_frames)
                    if hasattr(adapter, "video_num_frames")
                    and any(
                        Path(media).suffix.casefold()
                        in SUPPORTED_VIDEO_SUFFIXES
                        for task in tasks
                        for media in task.media
                    )
                    else None
                ),
            )
            if args.resume:
                existing_manifest = load_run_manifest(manifest_path)
                validate_resume_manifest(
                    existing_manifest,
                    manifest,
                    output_path=args.output,
                )
                existing_records = validate_resume_output(
                    tasks,
                    adapter,
                    args.output,
                    warmup=args.warmup,
                    repetitions=args.repetitions,
                    max_retries=args.max_retries,
                    timeout_seconds=args.attempt_timeout_seconds,
                )
                validate_resume_record_count(
                    existing_manifest,
                    len(existing_records),
                )
                manifest = prepare_resumed_manifest(existing_manifest)
            elif not args.overwrite and (
                args.output.exists() or manifest_path.exists()
            ):
                raise ManifestResumeError(
                    "output or manifest already exists; choose a new "
                    "--output, use --resume for an interrupted compatible "
                    "run, or pass --overwrite to replace it"
                )
            if not args.resume:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open(
                    "w",
                    encoding="utf-8",
                    newline="\n",
                ):
                    pass
                manifest = checkpoint_run_manifest(
                    manifest,
                    [],
                    output_path=args.output,
                )
            write_run_manifest(manifest_path, manifest)
            records = []

            def persist_checkpoint(
                current_records: tuple[RunRecord, ...],
            ) -> None:
                nonlocal manifest
                manifest = checkpoint_run_manifest(
                    manifest,
                    current_records,
                    output_path=args.output,
                )
                write_run_manifest(
                    manifest_path,
                    manifest,
                )

            try:
                records = run_benchmark(
                    tasks,
                    adapter,
                    args.output,
                    warmup=args.warmup,
                    repetitions=args.repetitions,
                    max_retries=args.max_retries,
                    timeout_seconds=args.attempt_timeout_seconds,
                    resume=args.resume,
                    on_record_persisted=persist_checkpoint,
                )
            except BaseException as exc:
                partial_records: list[dict[str, Any]] = []
                if args.output.is_file():
                    try:
                        partial_records = load_records(args.output)
                    except ReportError:
                        partial_records = []
                write_run_manifest(
                    manifest_path,
                    finalize_run_manifest(
                        manifest,
                        partial_records,
                        status="failed",
                        error=f"{type(exc).__name__}: {exc}",
                        output_path=args.output,
                    ),
                )
                raise
            write_run_manifest(
                manifest_path,
                finalize_run_manifest(
                    manifest,
                    records,
                    status="completed",
                    output_path=args.output,
                ),
            )
        except DatasetError as exc:
            print(f"Dataset error: {exc}", file=sys.stderr)
            return 2
        except (ManifestResumeError, ResumeError) as exc:
            print(f"Run error: {exc}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"Run error: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        print(f"Run contains {len(records)} records in {args.output}")
        print(f"Wrote run manifest to {manifest_path}")
        print(
            format_summary(
                summarize(
                    [
                        json.loads(line)
                        for line in args.output.read_text(
                            encoding="utf-8"
                        ).splitlines()
                    ]
                )
            )
        )
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

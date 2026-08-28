"""Run the installed core workflow as a bounded, offline contributor smoke test."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import sysconfig
import tempfile
import time
from pathlib import Path
from typing import Any

from openmultimodal_lab import __version__
from openmultimodal_lab.manifest import load_run_manifest, manifest_path_for
from openmultimodal_lab.reporting import load_records, summarize


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "examples" / "tasks" / "smoke.jsonl"
EXPECTED_RECORDS = 3
STEP_TIMEOUT_SECONDS = 20
NETWORK_GUARD = """\
import socket

_MESSAGE = "network disabled by contributor smoke"


def _blocked(*args, **kwargs):
    raise RuntimeError(_MESSAGE)


class _OfflineSocket(socket.socket):
    def connect(self, *args, **kwargs):
        raise RuntimeError(_MESSAGE)

    def connect_ex(self, *args, **kwargs):
        raise RuntimeError(_MESSAGE)


socket.socket = _OfflineSocket
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
"""


class SmokeError(RuntimeError):
    """A contributor smoke invariant failed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cli_path() -> Path:
    scripts_dir = Path(sysconfig.get_path("scripts"))
    name = "oml.exe" if os.name == "nt" else "oml"
    path = scripts_dir / name
    if not path.is_file():
        raise SmokeError(
            f"installed CLI not found at the interpreter scripts path: {path}"
        )
    return path


def _offline_environment(guard_dir: Path) -> dict[str, str]:
    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH")
    environment.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INDEX": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": (
                str(guard_dir)
                if not existing_pythonpath
                else os.pathsep.join((str(guard_dir), existing_pythonpath))
            ),
        }
    )
    return environment


def _verify_network_guard(*, cwd: Path, environment: dict[str, str]) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import socket; socket.create_connection(('example.com', 443))",
        ],
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=STEP_TIMEOUT_SECONDS,
    )
    guard_failed = (
        completed.returncode == 0
        or "network disabled by contributor smoke" not in completed.stderr
    )
    if guard_failed:
        raise SmokeError("network guard self-test did not block an outbound socket")


def _run_step(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=STEP_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SmokeError(
            f"{name} could not run: {type(exc).__name__}: {exc}"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        raise SmokeError(f"{name} exited {completed.returncode}: {detail}")
    if completed.stderr.strip():
        raise SmokeError(f"{name} emitted stderr: {completed.stderr.strip()}")
    return completed.stdout


def _validate_artifacts(output: Path) -> dict[str, Any]:
    manifest_path = manifest_path_for(output)
    if not output.is_file() or not manifest_path.is_file():
        raise SmokeError("mock run did not create both JSONL and manifest artifacts")

    records = load_records(output)
    summary = summarize(records)
    manifest = load_run_manifest(manifest_path)
    if len(records) != EXPECTED_RECORDS:
        raise SmokeError(
            f"expected {EXPECTED_RECORDS} records, found {len(records)}"
        )
    if summary["successful_tasks"] != EXPECTED_RECORDS:
        raise SmokeError("mock inference did not complete every smoke task")
    if manifest.get("status") != "completed":
        raise SmokeError(f"manifest status is {manifest.get('status')!r}, not completed")
    if manifest.get("records_written") != EXPECTED_RECORDS:
        raise SmokeError("manifest record count does not match the expected smoke grid")

    output_identity = manifest.get("output")
    if not isinstance(output_identity, dict):
        raise SmokeError("manifest output identity is missing")
    if output_identity.get("size_bytes") != output.stat().st_size:
        raise SmokeError("manifest output size does not match the JSONL artifact")
    if output_identity.get("sha256") != _sha256(output):
        raise SmokeError("manifest output hash does not match the JSONL artifact")
    return summary


def run_smoke() -> dict[str, Any]:
    if not DATASET.is_file():
        raise SmokeError(f"smoke dataset is missing: {DATASET}")

    cli = _cli_path()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="oml-contributor-smoke-") as temp_dir:
        workspace = Path(temp_dir)
        output = workspace / "smoke.jsonl"
        guard_dir = workspace / "network-guard"
        guard_dir.mkdir()
        (guard_dir / "sitecustomize.py").write_text(NETWORK_GUARD, encoding="utf-8")
        environment = _offline_environment(guard_dir)
        _verify_network_guard(cwd=workspace, environment=environment)
        version_output = _run_step(
            "CLI version",
            [str(cli), "--version"],
            cwd=workspace,
            environment=environment,
        )
        if version_output.strip() != f"oml {__version__}":
            raise SmokeError(
                f"unexpected CLI version output: {version_output.strip()!r}"
            )
        _run_step(
            "doctor",
            [str(cli), "doctor"],
            cwd=workspace,
            environment=environment,
        )
        _run_step(
            "mock run",
            [
                str(cli),
                "run",
                "--backend",
                "mock",
                "--dataset",
                str(DATASET),
                "--media-root",
                str(PROJECT_ROOT),
                "--output",
                str(output),
            ],
            cwd=workspace,
            environment=environment,
        )
        report_output = _run_step(
            "JSON report",
            [str(cli), "report", "--input", str(output), "--json"],
            cwd=workspace,
            environment=environment,
        )
        try:
            cli_summary = json.loads(report_output)
        except json.JSONDecodeError as exc:
            raise SmokeError(f"report output is not valid JSON: {exc}") from exc
        summary = _validate_artifacts(output)
        if cli_summary != summary:
            raise SmokeError("CLI report and direct evidence summary disagree")

    elapsed_seconds = time.monotonic() - started
    if elapsed_seconds >= 60:
        raise SmokeError(f"smoke test exceeded 60 seconds: {elapsed_seconds:.3f}")
    return {
        "status": "PASS",
        "package_version": __version__,
        "records": EXPECTED_RECORDS,
        "successful_records": EXPECTED_RECORDS,
        "artifacts_validated": ["smoke.jsonl", "smoke.jsonl.manifest.json"],
        "network_policy": "socket guard enforced in CLI subprocesses; mock backend",
        "elapsed_seconds": round(elapsed_seconds, 3),
    }


def main() -> int:
    try:
        result = run_smoke()
    except SmokeError as exc:
        print(f"Contributor smoke failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

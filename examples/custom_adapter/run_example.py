"""Run the fake third-party adapter through the real benchmark runner."""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from openmultimodal_lab.models import EvaluationTask
from openmultimodal_lab.runner import run_benchmark

from .fake_adapter import FakeBackendAdapter


def main() -> int:
    task = EvaluationTask(
        id="custom-adapter-smoke",
        prompt="Return a deterministic offline fixture response.",
        metadata={
            "category": "adapter-contract",
            "dataset_version": "custom-adapter-v1",
        },
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        records = run_benchmark(
            [task],
            FakeBackendAdapter(),
            Path(temp_dir) / "run.jsonl",
        )
    record = asdict(records[0])
    summary = {
        "backend": record["backend"],
        "model_revision": record["model_revision"],
        "response_text": record["response_text"],
        "status": record["status"],
        "usage": record["usage"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if record["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

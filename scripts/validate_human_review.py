"""Validate a task-by-task human review record bound to a dataset hash."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from openmultimodal_lab.datasets import DatasetError, load_tasks


REQUIRED_CHECKS = frozenset(
    {
        "media_opens_and_plays",
        "sampled_temporal_evidence_visible",
        "prompt_answer_matches_media",
        "answer_is_unambiguous",
        "license_and_provenance_confirmed",
    }
)
EXPECTED_SAMPLED_FRAME_INDICES = [0, 2, 4, 6, 8, 10, 12, 14]
EXPECTED_CONTACT_SHEET_ORDER = [0, 5, 10, 15]
MAX_REVIEW_BYTES = 8 * 1024 * 1024
MAX_DATASET_HASH_BYTES = 16 * 1024 * 1024


def _bounded_bytes(path: Path, limit: int, label: str) -> bytes:
    with path.open("rb") as handle:
        value = handle.read(limit + 1)
    if len(value) > limit:
        raise ValueError(
            f"{label} exceeds the {limit // (1024 * 1024)} MiB safety limit"
        )
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(
        _bounded_bytes(path, MAX_DATASET_HASH_BYTES, "dataset")
    ).hexdigest()


def audit_human_review(
    dataset_path: Path,
    review_path: Path,
) -> list[str]:
    """Return deterministic findings; an empty list means complete review."""

    try:
        tasks = load_tasks(dataset_path, require_media=False)
    except (DatasetError, OSError) as exc:
        return [f"dataset is unreadable: {type(exc).__name__}: {exc}"]
    try:
        review_raw = _bounded_bytes(review_path, MAX_REVIEW_BYTES, "review")
        review = json.loads(review_raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"review record is unreadable: {type(exc).__name__}"]
    if not isinstance(review, dict):
        return ["review record must be a JSON object"]

    findings: list[str] = []
    if review.get("schema_version") != "1.0":
        findings.append("review schema_version must be '1.0'")
    if review.get("sampled_frame_indices") != EXPECTED_SAMPLED_FRAME_INDICES:
        findings.append("review sampled_frame_indices do not match runtime")
    if review.get("contact_sheet_order") != EXPECTED_CONTACT_SHEET_ORDER:
        findings.append("review contact_sheet_order is invalid")
    try:
        expected_hash = _sha256(dataset_path)
    except (OSError, ValueError) as exc:
        return [f"dataset hash is unavailable: {type(exc).__name__}"]
    if review.get("dataset_sha256") != expected_hash:
        findings.append("review dataset_sha256 does not match the dataset")
    dataset_versions = {
        str(task.metadata.get("dataset_version", "")) for task in tasks
    }
    if len(dataset_versions) != 1:
        findings.append("dataset must contain exactly one dataset_version")
    elif review.get("dataset_version") not in dataset_versions:
        findings.append("review dataset_version does not match the tasks")

    entries = review.get("entries")
    if not isinstance(entries, list):
        return [*findings, "review entries must be a list"]
    entries_by_id: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            findings.append(f"review entry {index} must be an object")
            continue
        task_id = entry.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            findings.append(f"review entry {index} has an invalid task_id")
            continue
        if task_id in entries_by_id:
            findings.append(f"duplicate review entry for task '{task_id}'")
            continue
        entries_by_id[task_id] = entry

    tasks_by_id = {task.id: task for task in tasks}
    expected_ids = set(tasks_by_id)
    actual_ids = set(entries_by_id)
    for task_id in sorted(expected_ids - actual_ids):
        findings.append(f"missing review entry for task '{task_id}'")
    for task_id in sorted(actual_ids - expected_ids):
        findings.append(f"unexpected review entry for task '{task_id}'")

    for task_id in sorted(expected_ids & actual_ids):
        entry = entries_by_id[task_id]
        task_findings: list[str] = []
        if entry.get("media") != list(tasks_by_id[task_id].media):
            task_findings.append("media does not match the dataset")
        checks = entry.get("checks")
        if not isinstance(checks, dict):
            task_findings.append("checks must be an object")
        else:
            missing_checks = REQUIRED_CHECKS - set(checks)
            extra_checks = set(checks) - REQUIRED_CHECKS
            if missing_checks:
                task_findings.append(
                    f"missing checks {sorted(missing_checks)}"
                )
            if extra_checks:
                task_findings.append(
                    f"unknown checks {sorted(extra_checks)}"
                )
            not_approved = sorted(
                check
                for check in REQUIRED_CHECKS & set(checks)
                if checks[check] is not True
            )
            if not_approved:
                task_findings.append(
                    f"checks not approved {not_approved}"
                )
        reviewer = entry.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            task_findings.append("reviewer is missing")
        reviewed_at = entry.get("reviewed_at")
        if not isinstance(reviewed_at, str):
            task_findings.append("reviewed_at is missing")
        else:
            try:
                parsed_date = date.fromisoformat(reviewed_at)
            except ValueError:
                task_findings.append("reviewed_at is not YYYY-MM-DD")
            else:
                if parsed_date.isoformat() != reviewed_at:
                    task_findings.append("reviewed_at is not YYYY-MM-DD")
        if not isinstance(entry.get("notes", ""), str):
            task_findings.append("notes must be a string")
        if task_findings:
            findings.append(
                f"task '{task_id}' incomplete: " + "; ".join(task_findings)
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    args = parser.parse_args()

    findings = audit_human_review(args.dataset, args.review)
    if findings:
        for finding in findings:
            print(f"[OPEN] {finding}")
        print(f"Human review incomplete: {len(findings)} finding(s)")
        return 1
    print("Human review complete: every task is approved and hash-bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

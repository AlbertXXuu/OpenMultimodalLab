"""Deterministic, task-selected metrics for benchmark responses."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .models import EvaluationTask


@dataclass(frozen=True, slots=True)
class EvaluationScore:
    """One serializable deterministic evaluation result."""

    score: float | None
    matched: tuple[str, ...]
    name: str
    details: Mapping[str, Any]


def _normalized_text(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


def keyword_score(
    response: str,
    expected_keywords: tuple[str, ...],
) -> EvaluationScore:
    """Return case-insensitive phrase coverage, or no score without references."""

    if not expected_keywords:
        return EvaluationScore(
            score=None,
            matched=(),
            name="keyword_coverage",
            details={"total_references": 0},
        )

    normalized_response = " ".join(response.casefold().split())
    matched = tuple(
        keyword
        for keyword in expected_keywords
        if " ".join(keyword.casefold().split()) in normalized_response
    )
    return EvaluationScore(
        score=len(matched) / len(expected_keywords),
        matched=matched,
        name="keyword_coverage",
        details={"total_references": len(expected_keywords)},
    )


def normalized_exact_match(
    response: str,
    references: tuple[str, ...],
) -> EvaluationScore:
    """Match a constrained answer after case and punctuation normalization."""

    normalized_response = _normalized_text(response)
    normalized_references = tuple(_normalized_text(item) for item in references)
    matched = tuple(
        reference
        for reference, normalized in zip(
            references,
            normalized_references,
            strict=True,
        )
        if normalized_response == normalized
    )
    return EvaluationScore(
        score=1.0 if matched else 0.0,
        matched=matched[:1],
        name="normalized_exact_match",
        details={
            "normalized_response": normalized_response,
            "accepted_references": normalized_references,
        },
    )


_NUMERIC_TOKEN = re.compile(
    r"(?<!\w)[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\w)"
)


def numeric_tolerance_score(
    response: str,
    target: float,
    absolute_tolerance: float,
) -> EvaluationScore:
    """Compare one unambiguous numeric answer with an absolute tolerance."""

    candidates = tuple(
        float(match.group(0).replace(",", ""))
        for match in _NUMERIC_TOKEN.finditer(response)
    )
    absolute_error = (
        abs(candidates[0] - target) if len(candidates) == 1 else None
    )
    is_match = len(candidates) == 1 and math.isclose(
        candidates[0],
        target,
        rel_tol=0.0,
        abs_tol=absolute_tolerance,
    )
    return EvaluationScore(
        score=1.0 if is_match else 0.0,
        matched=(str(target),) if is_match else (),
        name="numeric_tolerance",
        details={
            "target": target,
            "absolute_tolerance": absolute_tolerance,
            "candidates": candidates,
            "candidate_count": len(candidates),
            "absolute_error": absolute_error,
            "ambiguous": len(candidates) > 1,
        },
    )


def _answer_units(response: str) -> list[tuple[str, tuple[str, ...]]]:
    """Split prose and Markdown lists into local units for attribute binding."""

    units: list[tuple[str, tuple[str, ...]]] = []
    for raw_line in response.splitlines() or [response]:
        line = raw_line.strip()
        if not line:
            continue

        is_list_item = bool(re.match(r"^(?:[-*+]|\d+[.)])\s+", line))
        cleaned = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", line)
        cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
        parts = (
            [cleaned]
            if is_list_item
            else re.split(r"[.!?;,:]+|\band\b", cleaned, flags=re.IGNORECASE)
        )
        for part in parts:
            normalized = _normalized_text(part)
            if normalized:
                units.append((part.strip(), tuple(normalized.split())))
    return units


def _find_group_occurrences(
    units: list[tuple[str, tuple[str, ...]]],
    group: tuple[str, ...],
) -> list[tuple[int, int]]:
    normalized_terms = tuple(_normalized_text(term) for term in group)
    occurrences: list[tuple[int, int]] = []

    for unit_index, (_, tokens) in enumerate(units):
        positions: list[int] = []
        for term in normalized_terms:
            term_tokens = term.split()
            position = next(
                (
                    index
                    for index in range(len(tokens) - len(term_tokens) + 1)
                    if tokens[index : index + len(term_tokens)] == tuple(term_tokens)
                ),
                None,
            )
            if position is None:
                break
            positions.append(position)
        else:
            occurrences.append((unit_index, min(positions)))

    return occurrences


def attribute_group_score(task: EvaluationTask, response: str) -> EvaluationScore:
    """Score locally bound attribute groups, optionally in expected order."""

    groups = task.scoring.groups
    units = _answer_units(response)
    labels = task.expected_keywords
    matched: list[str] = []
    group_results: list[dict[str, Any]] = []
    previous_position = (-1, -1)

    for label, group in zip(labels, groups, strict=True):
        occurrences = _find_group_occurrences(units, group)
        selected = next(
            (
                position
                for position in occurrences
                if not task.scoring.ordered or position > previous_position
            ),
            None,
        )
        is_match = selected is not None
        if is_match:
            matched.append(label)
            if task.scoring.ordered:
                previous_position = selected
        group_results.append(
            {
                "reference": label,
                "terms": group,
                "matched": is_match,
                "unit_index": selected[0] if selected is not None else None,
            }
        )

    return EvaluationScore(
        score=len(matched) / len(groups),
        matched=tuple(matched),
        name="attribute_groups",
        details={
            "ordered": task.scoring.ordered,
            "units": tuple(unit for unit, _ in units),
            "groups": tuple(group_results),
        },
    )


def score_response(task: EvaluationTask, response: str) -> EvaluationScore:
    """Dispatch to the deterministic scorer declared by the task."""

    if task.scoring.type == "keyword_coverage":
        return keyword_score(response, task.expected_keywords)
    if task.scoring.type == "normalized_exact_match":
        return normalized_exact_match(response, task.expected_keywords)
    if task.scoring.type == "attribute_groups":
        return attribute_group_score(task, response)
    if task.scoring.type == "numeric_tolerance":
        if (
            task.scoring.target is None
            or task.scoring.absolute_tolerance is None
        ):
            raise ValueError("numeric tolerance scorer is missing its reference")
        return numeric_tolerance_score(
            response,
            task.scoring.target,
            task.scoring.absolute_tolerance,
        )
    raise ValueError(f"unsupported scoring type '{task.scoring.type}'")

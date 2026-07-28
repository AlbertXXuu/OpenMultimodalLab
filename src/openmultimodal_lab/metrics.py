"""Deterministic metrics for the first benchmark milestone."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeywordScore:
    """Keyword coverage for one response."""

    score: float | None
    matched: tuple[str, ...]


def keyword_score(response: str, expected_keywords: tuple[str, ...]) -> KeywordScore:
    """Return case-insensitive phrase coverage, or no score without references."""

    if not expected_keywords:
        return KeywordScore(score=None, matched=())

    normalized_response = " ".join(response.casefold().split())
    matched = tuple(
        keyword
        for keyword in expected_keywords
        if " ".join(keyword.casefold().split()) in normalized_response
    )
    return KeywordScore(score=len(matched) / len(expected_keywords), matched=matched)

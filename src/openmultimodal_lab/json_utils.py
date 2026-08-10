"""Strict JSON helpers shared by public input boundaries."""

from __future__ import annotations

import json
from typing import Any


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant '{value}'")


def strict_json_loads(value: str | bytes) -> Any:
    """Decode standards-compliant JSON and reject NaN or infinities."""

    return json.loads(value, parse_constant=_reject_nonstandard_constant)

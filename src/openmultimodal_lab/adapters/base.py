"""Contract implemented by all model adapters."""

from __future__ import annotations

from typing import Protocol

from ..models import EvaluationTask, ModelOutput


class ModelAdapter(Protocol):
    """Minimal synchronous adapter contract for the first milestone."""

    name: str

    def generate(self, task: EvaluationTask) -> ModelOutput:
        """Generate a normalized response for one task."""
        ...

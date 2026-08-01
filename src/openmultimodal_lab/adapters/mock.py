"""Deterministic offline adapter used to test the benchmark infrastructure."""

from __future__ import annotations

from ..models import EvaluationTask, ModelOutput


class MockAdapter:
    """Return deterministic text without loading or calling a real model."""

    name = "mock"
    revision = "deterministic-v1"

    def generate(
        self,
        task: EvaluationTask,
        *,
        timeout_seconds: float | None = None,
    ) -> ModelOutput:
        del timeout_seconds
        if (
            task.scoring.type == "normalized_exact_match"
            and task.expected_keywords
        ):
            response = task.expected_keywords[0]
        elif (
            task.scoring.type == "numeric_tolerance"
            and task.scoring.target is not None
        ):
            response = str(task.scoring.target)
        elif task.expected_keywords:
            response = "Mock observation: " + ", ".join(task.expected_keywords) + "."
        else:
            response = f"Mock response for task {task.id}."

        return ModelOutput(
            text=response,
            backend=self.name,
            model_revision=self.revision,
            usage={"is_test_backend": True},
        )

"""Deterministic offline adapter used to test the benchmark infrastructure."""

from __future__ import annotations

from ..models import EvaluationTask, ModelOutput


class MockAdapter:
    """Return deterministic text without loading or calling a real model."""

    name = "mock"
    revision = "deterministic-v1"

    def generate(self, task: EvaluationTask) -> ModelOutput:
        if task.expected_keywords:
            response = "Mock observation: " + ", ".join(task.expected_keywords) + "."
        else:
            response = f"Mock response for task {task.id}."

        return ModelOutput(
            text=response,
            backend=self.name,
            model_revision=self.revision,
            usage={"is_test_backend": True},
        )

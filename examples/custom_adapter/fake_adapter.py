"""Dependency-free adapter around a deterministic fake third-party backend."""

from __future__ import annotations

import hashlib

from openmultimodal_lab.adapters.errors import (
    AdapterInputError,
    AdapterTimeoutError,
)
from openmultimodal_lab.models import EvaluationTask, ModelOutput


FAKE_BACKEND_BEHAVIOR = "normalize-whitespace;sha256-12;offline:v1"
FAKE_BACKEND_REVISION = (
    "fake-backend@sha256:"
    + hashlib.sha256(FAKE_BACKEND_BEHAVIOR.encode("utf-8")).hexdigest()
)


class FakeBackendInputError(ValueError):
    """The fake provider rejected an input before generation."""


class FakeBackendDeadlineExceeded(TimeoutError):
    """The fake provider cannot finish within the supplied deadline."""


class FakeBackendClient:
    """Small stand-in for an SDK client owned by another provider."""

    minimum_deadline_seconds = 0.001

    def complete(
        self,
        prompt: str,
        *,
        timeout_seconds: float | None,
    ) -> str:
        normalized_prompt = " ".join(prompt.split())
        if not normalized_prompt:
            raise FakeBackendInputError("prompt must contain visible text")
        if (
            timeout_seconds is not None
            and timeout_seconds < self.minimum_deadline_seconds
        ):
            raise FakeBackendDeadlineExceeded(
                "deadline is below the fake backend minimum"
            )
        digest = hashlib.sha256(
            normalized_prompt.encode("utf-8")
        ).hexdigest()[:12]
        return f"offline fixture response {digest}"


class FakeBackendAdapter:
    """Translate the fake provider contract into OpenMultimodalLab types."""

    name = "third-party-fake"

    def __init__(self, client: FakeBackendClient | None = None) -> None:
        self._client = client if client is not None else FakeBackendClient()

    @property
    def revision(self) -> str:
        """Return the content-addressed behavior revision."""
        return FAKE_BACKEND_REVISION

    def generate(
        self,
        task: EvaluationTask,
        *,
        timeout_seconds: float | None = None,
    ) -> ModelOutput:
        try:
            text = self._client.complete(
                task.prompt,
                timeout_seconds=timeout_seconds,
            )
        except FakeBackendInputError as exc:
            raise AdapterInputError(str(exc)) from exc
        except FakeBackendDeadlineExceeded as exc:
            raise AdapterTimeoutError(str(exc)) from exc

        return ModelOutput(
            text=text,
            backend=self.name,
            model_revision=self.revision,
            usage={
                "provider": "fake-backend",
                "behavior_spec": FAKE_BACKEND_BEHAVIOR,
                "deterministic": True,
                "input_characters": len(task.prompt),
            },
        )

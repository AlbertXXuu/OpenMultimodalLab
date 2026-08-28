"""Reusable assertions for the custom adapter example."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from openmultimodal_lab.models import EvaluationTask, ModelOutput


REQUIRED_ADAPTER_FIELDS = ("name", "revision", "generate")


class AdapterContractError(AssertionError):
    """An adapter does not meet the documented integration contract."""


def assert_adapter_contract(adapter: Any, task: EvaluationTask) -> None:
    """Check identity, output shape and deterministic repeated generation."""
    for field_name in REQUIRED_ADAPTER_FIELDS:
        if not hasattr(adapter, field_name):
            raise AdapterContractError(
                f"adapter is missing required field '{field_name}'"
            )

    if not isinstance(adapter.name, str) or not adapter.name.strip():
        raise AdapterContractError("adapter 'name' must be a non-empty string")
    if not isinstance(adapter.revision, str) or not adapter.revision.strip():
        raise AdapterContractError(
            "adapter 'revision' must be a non-empty immutable identifier"
        )
    if not callable(adapter.generate):
        raise AdapterContractError("adapter 'generate' must be callable")

    first = adapter.generate(task)
    second = adapter.generate(task)
    for output in (first, second):
        if not isinstance(output, ModelOutput):
            raise AdapterContractError(
                "adapter 'generate' must return ModelOutput"
            )
        if not isinstance(output.text, str):
            raise AdapterContractError("ModelOutput 'text' must be a string")
        if output.backend != adapter.name:
            raise AdapterContractError(
                "ModelOutput 'backend' must equal adapter 'name'"
            )
        if output.model_revision != adapter.revision:
            raise AdapterContractError(
                "ModelOutput 'model_revision' must equal adapter 'revision'"
            )
        if not isinstance(output.usage, Mapping):
            raise AdapterContractError("ModelOutput 'usage' must be a mapping")
        try:
            json.dumps(output.usage, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise AdapterContractError(
                "ModelOutput 'usage' must contain only finite JSON values"
            ) from exc
    if first != second:
        raise AdapterContractError(
            "repeated generation changed under one fixed task and revision"
        )

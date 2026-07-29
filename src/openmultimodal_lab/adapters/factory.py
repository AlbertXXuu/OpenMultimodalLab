"""Construct built-in adapters from stable CLI backend names."""

from __future__ import annotations

from pathlib import Path

from .base import ModelAdapter
from .mock import MockAdapter
from .qwen3_vl import (
    DEFAULT_MODEL_ID,
    DEFAULT_MODEL_REVISION,
    Qwen3VLAdapter,
)

BACKEND_NAMES = ("mock", "qwen3-vl")


def create_adapter(
    backend: str,
    *,
    media_root: str | Path = ".",
    model_id: str | None = None,
    revision: str | None = None,
    max_new_tokens: int = 128,
) -> ModelAdapter:
    """Create one built-in adapter without eagerly loading model weights."""

    if backend == "mock":
        return MockAdapter()
    if backend == "qwen3-vl":
        return Qwen3VLAdapter(
            media_root=media_root,
            model_id=model_id or DEFAULT_MODEL_ID,
            revision=revision or DEFAULT_MODEL_REVISION,
            max_new_tokens=max_new_tokens,
        )
    raise ValueError(f"Unsupported backend: {backend}")

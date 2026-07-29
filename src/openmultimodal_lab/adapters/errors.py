"""Typed adapter failures that become stable benchmark record statuses."""

from __future__ import annotations


class AdapterError(RuntimeError):
    """Base class for failures raised at the model adapter boundary."""

    status = "generation_error"


class AdapterInputError(AdapterError):
    """Raised when a task cannot be represented by an adapter."""

    status = "invalid_task"


class AdapterDependencyError(AdapterError):
    """Raised when optional packages required by an adapter are unavailable."""

    status = "model_load_error"


class ModelLoadError(AdapterError):
    """Raised when model or processor initialization fails."""

    status = "model_load_error"


class AdapterOutOfMemoryError(AdapterError):
    """Raised when an adapter exhausts accelerator memory."""

    status = "out_of_memory"

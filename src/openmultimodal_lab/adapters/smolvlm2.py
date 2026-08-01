"""Local Transformers adapter for SmolVLM2 instruction models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import AdapterDependencyError
from .transformers_image_text import (
    DEFAULT_VIDEO_NUM_FRAMES,
    TransformersDependencies,
    TransformersImageTextAdapter,
)

DEFAULT_MODEL_ID = "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
DEFAULT_MODEL_REVISION = "7b375e1b73b11138ff12fe22c8f2822d8fe03467"


def _load_dependencies() -> TransformersDependencies:
    try:
        import av  # noqa: F401 - selected local video decoding backend
        import num2words  # noqa: F401 - required by the SmolVLM processor
        import torch
        from PIL import Image
        from transformers import AutoModelForImageTextToText, AutoProcessor
        from transformers.video_utils import load_video
    except ImportError as exc:
        raise AdapterDependencyError(
            "SmolVLM2 dependencies are missing. Install the 'smolvlm2' "
            "optional dependency group in a Python 3.11/3.12 environment."
        ) from exc

    return TransformersDependencies(
        torch=torch,
        auto_model=AutoModelForImageTextToText,
        auto_processor=AutoProcessor,
        image_module=Image,
        video_loader=load_video,
    )


class SmolVLM2Adapter(TransformersImageTextAdapter):
    """Run the pinned SmolVLM2 500M checkpoint through Transformers."""

    name = "smolvlm2"
    display_name = "SmolVLM2"

    def __init__(
        self,
        *,
        media_root: str | Path = ".",
        model_id: str = DEFAULT_MODEL_ID,
        revision: str = DEFAULT_MODEL_REVISION,
        max_new_tokens: int = 128,
        video_num_frames: int = DEFAULT_VIDEO_NUM_FRAMES,
    ) -> None:
        super().__init__(
            media_root=media_root,
            model_id=model_id,
            revision=revision,
            max_new_tokens=max_new_tokens,
            video_num_frames=video_num_frames,
        )

    def _load_runtime_dependencies(self) -> TransformersDependencies:
        return _load_dependencies()

    def _model_load_kwargs(
        self,
        dependencies: TransformersDependencies,
    ) -> dict[str, Any]:
        return {
            "dtype": dependencies.torch.bfloat16,
            "device_map": "auto",
            "low_cpu_mem_usage": True,
        }

    def _move_inputs_to_model(self, inputs: Any) -> Any:
        assert self._dependencies is not None
        return inputs.to(
            self._model.device,
            dtype=self._dependencies.torch.bfloat16,
        )

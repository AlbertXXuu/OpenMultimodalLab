"""Local Transformers adapter for Qwen3-VL instruction models."""

from __future__ import annotations

from pathlib import Path

from .errors import AdapterDependencyError
from .transformers_image_text import (
    DEFAULT_VIDEO_NUM_FRAMES,
    TransformersDependencies,
    TransformersImageTextAdapter,
)

DEFAULT_MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
DEFAULT_MODEL_REVISION = "89644892e4d85e24eaac8bacfd4f463576704203"


def _load_dependencies() -> TransformersDependencies:
    try:
        import av  # noqa: F401 - selected local video decoding backend
        import torch
        from PIL import Image
        from transformers import AutoModelForImageTextToText, AutoProcessor
        from transformers.video_utils import load_video
    except ImportError as exc:
        raise AdapterDependencyError(
            "Qwen3-VL dependencies are missing. Install the 'qwen3-vl' "
            "optional dependency group in a Python 3.11/3.12 environment."
        ) from exc

    return TransformersDependencies(
        torch=torch,
        auto_model=AutoModelForImageTextToText,
        auto_processor=AutoProcessor,
        image_module=Image,
        video_loader=load_video,
    )


class Qwen3VLAdapter(TransformersImageTextAdapter):
    """Run a pinned Qwen3-VL checkpoint locally through Transformers."""

    name = "qwen3-vl"
    display_name = "Qwen3-VL"

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

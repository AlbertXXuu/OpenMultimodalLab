from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openmultimodal_lab.adapters import MockAdapter
from openmultimodal_lab.models import EvaluationTask, ModelOutput
from openmultimodal_lab.runner import run_benchmark
from openmultimodal_lab.studio import (
    DEVELOPER_ID,
    MAX_REPORT_ROWS,
    PLAYGROUND_MAX_NEW_TOKENS,
    PLAYGROUND_MAX_TIMEOUT_SECONDS,
    STUDIO_BRAND,
    STUDIO_NAME,
    STUDIO_TAGLINE,
    StudioInputError,
    StudioRuntime,
    load_report_view,
    safe_studio_error,
    select_media,
)
from openmultimodal_lab.studio_assets import (
    BRAND_HEADER_HTML,
    EASTER_EGG_JS,
    STUDIO_CSS,
)
from openmultimodal_lab.studio_ui import (
    _open_report,
    _run_playground,
    build_app,
    launch_studio,
)


class RecordingAdapter:
    name = "recording"
    revision = "revision-1"

    def __init__(self, *, media_root: Path, max_new_tokens: int) -> None:
        self.media_root = media_root
        self.max_new_tokens = max_new_tokens
        self.calls: list[tuple[EvaluationTask, float | None]] = []

    def generate(
        self,
        task: EvaluationTask,
        *,
        timeout_seconds: float | None = None,
    ) -> ModelOutput:
        self.calls.append((task, timeout_seconds))
        return ModelOutput(
            text="A blue circle.",
            backend=self.name,
            model_revision=self.revision,
            usage={
                "ttft_ms": 12.5,
                "output_tokens_per_second": 20.0,
                "peak_gpu_memory_mb": 512.0,
            },
        )


class StudioRuntimeTests(unittest.TestCase):
    def _media(self, root: Path, name: str = "sample.png") -> Path:
        path = root / name
        path.write_bytes(b"not-decoded-by-test")
        return path

    def test_select_media_requires_exactly_one_supported_nonempty_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image = self._media(root)
            video = self._media(root, "sample.mp4")
            unsupported = self._media(root, "sample.exe")

            self.assertEqual(select_media(image, None), (image.resolve(), "image"))
            with self.assertRaisesRegex(StudioInputError, "upload one"):
                select_media(None, None)
            with self.assertRaisesRegex(StudioInputError, "either"):
                select_media(image, video)
            with self.assertRaisesRegex(StudioInputError, "unsupported image"):
                select_media(unsupported, None)

    def test_runtime_reuses_one_backend_and_preserves_unscored_boundary(self) -> None:
        created: list[RecordingAdapter] = []

        def factory(
            backend: str,
            *,
            media_root: Path,
            max_new_tokens: int,
        ) -> RecordingAdapter:
            del backend
            adapter = RecordingAdapter(
                media_root=media_root,
                max_new_tokens=max_new_tokens,
            )
            created.append(adapter)
            return adapter

        runtime = StudioRuntime(adapter_factory=factory)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = self._media(root, "first.png")
            second_root = root / "second"
            second_root.mkdir()
            second = self._media(second_root, "second.jpg")

            result = runtime.run_playground(
                backend="mock",
                prompt="  Describe it.  ",
                image_path=first,
                video_path=None,
                max_new_tokens=32,
                timeout_seconds=60,
            )
            runtime.run_playground(
                backend="mock",
                prompt="Read it.",
                image_path=second,
                video_path=None,
                max_new_tokens=48,
                timeout_seconds=90,
            )

        self.assertEqual(len(created), 1)
        self.assertEqual(result.response_text, "A blue circle.")
        self.assertEqual(result.usage["ttft_ms"], 12.5)
        self.assertEqual(created[0].max_new_tokens, 48)
        self.assertEqual(created[0].media_root, second.parent.resolve())
        task, timeout = created[0].calls[0]
        self.assertEqual(task.prompt, "Describe it.")
        self.assertEqual(task.metadata["category"], "unscored-playground")
        self.assertEqual(task.expected_keywords, ())
        self.assertEqual(timeout, 60.0)

    def test_runtime_switches_backend_and_validates_parameters(self) -> None:
        backends: list[str] = []

        def factory(backend: str, **kwargs: object) -> RecordingAdapter:
            backends.append(backend)
            return RecordingAdapter(
                media_root=kwargs["media_root"],
                max_new_tokens=kwargs["max_new_tokens"],
            )

        runtime = StudioRuntime(adapter_factory=factory)
        with tempfile.TemporaryDirectory() as temp_dir:
            media = self._media(Path(temp_dir))
            for backend in ("mock", "qwen3-vl"):
                runtime.run_playground(
                    backend=backend,
                    prompt="Describe.",
                    image_path=media,
                    video_path=None,
                    max_new_tokens=16,
                    timeout_seconds=30,
                )
            with self.assertRaisesRegex(StudioInputError, "prompt cannot be empty"):
                runtime.run_playground(
                    backend="mock",
                    prompt=" ",
                    image_path=media,
                    video_path=None,
                    max_new_tokens=16,
                    timeout_seconds=30,
                )
            with self.assertRaisesRegex(StudioInputError, "unsupported backend"):
                runtime.run_playground(
                    backend="unknown",
                    prompt="Describe.",
                    image_path=media,
                    video_path=None,
                    max_new_tokens=16,
                    timeout_seconds=30,
                )
            with self.assertRaisesRegex(StudioInputError, "max new tokens"):
                runtime.run_playground(
                    backend="mock",
                    prompt="Describe.",
                    image_path=media,
                    video_path=None,
                    max_new_tokens=PLAYGROUND_MAX_NEW_TOKENS + 1,
                    timeout_seconds=30,
                )
            with self.assertRaisesRegex(StudioInputError, "timeout"):
                runtime.run_playground(
                    backend="mock",
                    prompt="Describe.",
                    image_path=media,
                    video_path=None,
                    max_new_tokens=16,
                    timeout_seconds=PLAYGROUND_MAX_TIMEOUT_SECONDS + 1,
                )

        self.assertEqual(backends, ["mock", "qwen3-vl"])

    def test_report_view_is_read_only_and_bounded(self) -> None:
        task = EvaluationTask(
            id="task-1",
            prompt="Describe.",
            expected_keywords=("blue",),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "run.jsonl"
            run_benchmark([task], MockAdapter(), source)
            before = source.read_bytes()
            view = load_report_view(source)
            after = source.read_bytes()

            self.assertEqual(view.filename, "run.jsonl")
            self.assertEqual(len(view.rows), 1)
            self.assertEqual(view.rows[0][2], "task-1")
            self.assertEqual(before, after)

            with patch(
                "openmultimodal_lab.studio.MAX_REPORT_ROWS",
                0,
            ), self.assertRaisesRegex(StudioInputError, "more than"):
                load_report_view(source)

            wrong_type = Path(temp_dir) / "run.txt"
            wrong_type.write_bytes(before)
            with self.assertRaisesRegex(StudioInputError, "must be a .jsonl"):
                load_report_view(wrong_type)

        self.assertEqual(MAX_REPORT_ROWS, 2_000)

    def test_ui_wrappers_return_safe_errors(self) -> None:
        response, metrics, status = _run_playground(
            StudioRuntime(),
            "mock",
            "C:" + "\\Users\\Albert\\missing.png",
            None,
            "Describe.",
            32,
            60,
        )
        self.assertEqual(response, "")
        self.assertIn("LIVE METRICS", metrics)
        self.assertNotIn("Albert", status)

        summary, text, rows = _open_report(None)
        self.assertIn("Select a JSONL", summary)
        self.assertEqual(text, "")
        self.assertEqual(rows, [])

    def test_ui_playground_wrapper_completes_with_mock_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media = self._media(Path(temp_dir))
            response, metrics, status = _run_playground(
                StudioRuntime(),
                "mock",
                str(media),
                None,
                "Describe.",
                32,
                60,
            )

        self.assertTrue(response)
        self.assertIn("UNSCORED", metrics)
        self.assertIn("Completed locally", status)

    def test_brand_assets_are_local_and_include_accessible_developer_signal(self) -> None:
        combined = BRAND_HEADER_HTML + STUDIO_CSS + EASTER_EGG_JS
        self.assertIn(STUDIO_BRAND, combined)
        self.assertIn(STUDIO_NAME, combined)
        self.assertIn(STUDIO_TAGLINE, combined)
        self.assertIn(DEVELOPER_ID, combined)
        self.assertNotIn("<svg", BRAND_HEADER_HTML.casefold())
        self.assertIn("event.altKey", EASTER_EGG_JS)
        self.assertIn('event.key.toLowerCase() === "a"', EASTER_EGG_JS)
        self.assertNotIn("http://", combined)
        self.assertNotIn("https://", combined)

    def test_studio_uses_an_explicit_light_surface_palette(self) -> None:
        self.assertIn("--ail-bg: #ffffff", STUDIO_CSS)
        self.assertIn("--ail-panel: #ffffff", STUDIO_CSS)
        self.assertIn("--ail-text: #0f172a", STUDIO_CSS)
        self.assertIn("color-scheme: light", STUDIO_CSS)
        self.assertNotIn("--ail-bg: #070b12", STUDIO_CSS)
        self.assertNotIn("--ail-panel: #0d1420", STUDIO_CSS)

    def test_safe_error_redacts_absolute_paths(self) -> None:
        local_path = "C:" + "\\Users\\Albert\\secret.png"
        result = safe_studio_error(ValueError(local_path))
        self.assertNotIn("Albert", result)
        self.assertIn("<local-path>", result)


@unittest.skipUnless(
    importlib.util.find_spec("gradio") is not None,
    "optional Gradio dependency is not installed",
)
class StudioGradioTests(unittest.TestCase):
    @unittest.skipIf(
        sys.platform == "win32",
        "Gradio 6.22 leaves build-only event-loop resources on Windows",
    )
    def test_app_builds_with_private_event_endpoints(self) -> None:
        app = build_app()
        try:
            dependencies = app.config["dependencies"]
            self.assertEqual(len(dependencies), 3)
            self.assertTrue(
                all(
                    item["api_visibility"] == "private"
                    for item in dependencies
                )
            )
            self.assertFalse(app.config["analytics_enabled"])
            image_components = [
                item
                for item in app.config["components"]
                if item["props"].get("label")
                == "Image or document screenshot"
            ]
            self.assertEqual(len(image_components), 1)
            self.assertIsNone(image_components[0]["props"].get("format"))
        finally:
            app.close(verbose=False)

    def test_launch_forces_local_security_controls(self) -> None:
        class FakeApp:
            def __init__(self) -> None:
                self.kwargs: dict[str, object] = {}

            def launch(self, **kwargs: object) -> str:
                self.kwargs = kwargs
                return "launched"

        fake = FakeApp()
        with patch(
            "openmultimodal_lab.studio_ui.build_app",
            return_value=fake,
        ):
            result = launch_studio(
                host="127.0.0.1",
                port=8765,
                inbrowser=False,
            )
        self.assertEqual(result, "launched")
        self.assertEqual(fake.kwargs["server_name"], "127.0.0.1")
        self.assertFalse(fake.kwargs["share"])
        self.assertEqual(fake.kwargs["allowed_paths"], [])
        self.assertFalse(fake.kwargs["enable_monitoring"])
        self.assertTrue(fake.kwargs["strict_cors"])

        with self.assertRaisesRegex(ValueError, "loopback"):
            launch_studio(host="0.0.0.0")
        with self.assertRaisesRegex(ValueError, "port"):
            launch_studio(port=0)

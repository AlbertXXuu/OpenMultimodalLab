from __future__ import annotations

import base64
import hashlib
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
    PLAYGROUND_UI_DEFAULT_NEW_TOKENS,
    PLAYGROUND_UI_DEFAULT_TIMEOUT_SECONDS,
    PLAYGROUND_UI_MIN_NEW_TOKENS,
    PLAYGROUND_UI_MIN_TIMEOUT_SECONDS,
    STUDIO_BRAND,
    STUDIO_NAME,
    STUDIO_TAGLINE,
    StudioInputError,
    StudioRuntime,
    PlaygroundResult,
    VideoUploadInfo,
    inspect_video_upload,
    load_report_view,
    safe_studio_error,
    select_media,
)
from openmultimodal_lab.studio_assets import (
    ALVENX_WORDMARK_SHA256,
    BRAND_HEADER_HTML,
    CLEARED_STATUS_HTML,
    EASTER_EGG_JS,
    EMPTY_METRICS_HTML,
    EMPTY_STATUS_HTML,
    IMAGE_UPLOAD_GUIDANCE_HTML,
    INSTRUMENT_SANS_REVISION,
    INSTRUMENT_SANS_SHA256,
    STUDIO_CSS,
    VIDEO_UPLOAD_GUIDANCE_HTML,
    WORKSPACE_INPUT_HEADER_HTML,
    WORKSPACE_OUTPUT_HEADER_HTML,
    render_playground_metrics,
    render_success_status,
    render_video_upload_info,
)
from openmultimodal_lab.studio_ui import (
    DEFAULT_PROMPT,
    _clear_workspace,
    _default_prompt_if_empty,
    _inspect_video_upload,
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

    def test_clear_workspace_removes_hidden_media_prompt_and_output(self) -> None:
        cleared = _clear_workspace()

        self.assertEqual(cleared[:4], (None, None, "", ""))
        self.assertEqual(cleared[4], EMPTY_METRICS_HTML)
        self.assertEqual(cleared[5], CLEARED_STATUS_HTML)
        self.assertEqual(cleared[6], VIDEO_UPLOAD_GUIDANCE_HTML)
        self.assertIn("remains warm", cleared[5])

    def test_empty_ui_prompt_falls_back_to_the_visible_default(self) -> None:
        self.assertEqual(_default_prompt_if_empty(""), DEFAULT_PROMPT)
        self.assertEqual(_default_prompt_if_empty("   "), DEFAULT_PROMPT)
        self.assertEqual(
            _default_prompt_if_empty("What color is the car?"),
            "What color is the car?",
        )

    def test_ui_playground_wrapper_completes_with_mock_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            media = self._media(Path(temp_dir))
            response, metrics, status = _run_playground(
                StudioRuntime(),
                "mock",
                str(media),
                None,
                "   ",
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
        self.assertIn("data:image/svg+xml;base64,", BRAND_HEADER_HTML)
        self.assertIn('class="brand-wordmark-image"', BRAND_HEADER_HTML)
        self.assertIn("width: clamp(150px,13.5vw,178px)", STUDIO_CSS)
        self.assertNotIn("transform: translateY(-12px)", STUDIO_CSS)
        self.assertNotIn("<svg", BRAND_HEADER_HTML.casefold())
        self.assertIn("event.altKey", EASTER_EGG_JS)
        self.assertIn('event.key.toLowerCase() === "a"', EASTER_EGG_JS)
        self.assertNotIn("http://", combined)
        self.assertNotIn("https://", combined)

    def test_studio_uses_an_explicit_light_surface_palette(self) -> None:
        self.assertIn("--alx-bg: #ffffff", STUDIO_CSS)
        self.assertIn("--alx-panel: #ffffff", STUDIO_CSS)
        self.assertIn("--alx-text: #0f172a", STUDIO_CSS)
        self.assertIn("color-scheme: light", STUDIO_CSS)
        self.assertNotIn("--alx-bg: #070b12", STUDIO_CSS)
        self.assertNotIn("--alx-panel: #0d1420", STUDIO_CSS)

    def test_studio_uses_one_locked_brand_type_system(self) -> None:
        self.assertIn('font-family: "Instrument Sans"', STUDIO_CSS)
        self.assertIn('--alx-font-sans: "Instrument Sans"', STUDIO_CSS)
        self.assertIn('font-feature-settings: "ss01" 1, "ss02" 1', STUDIO_CSS)
        self.assertNotIn('class="brand-ai"', BRAND_HEADER_HTML)
        self.assertIn("text-transform: uppercase", STUDIO_CSS)
        self.assertIn("font-variant-numeric: tabular-nums", STUDIO_CSS)
        self.assertEqual(STUDIO_CSS.count("linear-gradient"), 2)
        self.assertIn("var(--alx-blue) 0%", STUDIO_CSS)
        self.assertNotIn("#0f766e", STUDIO_CSS)
        self.assertNotIn("--alx-teal", STUDIO_CSS)
        self.assertNotIn(
            "font-family: Arial, Helvetica, ui-sans-serif, sans-serif",
            STUDIO_CSS,
        )

    def test_vendored_brand_font_is_integrity_and_license_bound(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        font_root = project_root / "src/openmultimodal_lab/assets/fonts"
        encoded = "".join(
            (font_root / "InstrumentSans-wdth-wght.woff2.b64")
            .read_text(encoding="ascii")
            .split()
        )
        payload = base64.b64decode(encoded, validate=True)
        license_text = (font_root / "InstrumentSans-OFL.txt").read_text(
            encoding="utf-8"
        )

        self.assertEqual(payload[:4], b"wOF2")
        self.assertEqual(hashlib.sha256(payload).hexdigest(), INSTRUMENT_SANS_SHA256)
        self.assertEqual(
            INSTRUMENT_SANS_REVISION,
            "7fa22308a3d0c94ee2b3cd537a1196b65db34a3e",
        )
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", license_text)

    def test_public_wordmark_uses_portable_font_outlines(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        source = project_root / "docs/assets/alvenx-wordmark.svg"
        packaged = (
            project_root
            / "src/openmultimodal_lab/assets/brand/alvenx-wordmark.svg.b64"
        )
        source_bytes = source.read_bytes()
        packaged_bytes = base64.b64decode(
            "".join(packaged.read_text(encoding="ascii").split()),
            validate=True,
        )
        wordmark = source_bytes.decode("utf-8")

        self.assertEqual(packaged_bytes, source_bytes)
        self.assertEqual(
            hashlib.sha256(source_bytes).hexdigest(),
            ALVENX_WORDMARK_SHA256,
        )
        self.assertIn("Instrument Sans outlines", wordmark)
        self.assertGreaterEqual(wordmark.count('class="accent"'), 1)
        self.assertIn('id="brand-gradient"', wordmark)
        self.assertIn('gradientUnits="userSpaceOnUse"', wordmark)
        self.assertIn('stop-color="#4f8cff"', wordmark)
        self.assertIn('stop-color="#1e3a8a"', wordmark)
        self.assertIn('id="brand-l"', wordmark)
        self.assertIn('id="brand-Al"', wordmark)
        self.assertIn('href="#brand-Al"', wordmark)
        self.assertIn('href="#brand-v" x="935"', wordmark)
        self.assertIn('transform="translate(8.937 92)', wordmark)
        self.assertIn('transform="translate(19.936 126)', wordmark)
        self.assertIn('id="brand-nX-ligature"', wordmark)
        self.assertIn('href="#brand-X" x="2426.626"', wordmark)
        self.assertNotIn("teal", wordmark.casefold())
        self.assertGreater(wordmark.count("<path"), 10)
        self.assertNotIn("<text", wordmark)
        self.assertNotIn("font-family", wordmark)

    def test_media_guidance_documents_bounded_aspect_safe_inputs(self) -> None:
        self.assertIn("25 MiB", IMAGE_UPLOAD_GUIDANCE_HTML)
        self.assertIn("never crops", IMAGE_UPLOAD_GUIDANCE_HTML)
        self.assertIn("50 MiB", VIDEO_UPLOAD_GUIDANCE_HTML)
        self.assertIn("60 seconds", VIDEO_UPLOAD_GUIDANCE_HTML)
        self.assertIn("H.265/HEVC", VIDEO_UPLOAD_GUIDANCE_HTML)
        self.assertIn("object-fit: contain", STUDIO_CSS)
        self.assertIn("max-height: 360px", STUDIO_CSS)
        self.assertIn("height: auto !important", STUDIO_CSS)
        self.assertIn("max-width: 100% !important", STUDIO_CSS)
        self.assertNotIn(
            ".studio-media-input { height: 210px !important",
            STUDIO_CSS,
        )
        self.assertNotIn(
            ".studio-media-input { height: 180px !important",
            STUDIO_CSS,
        )

    def test_workspace_is_function_first_and_visually_grouped(self) -> None:
        workspace = (
            WORKSPACE_INPUT_HEADER_HTML
            + WORKSPACE_OUTPUT_HEADER_HTML
            + STUDIO_CSS
        )

        self.assertIn("INPUT", workspace)
        self.assertIn("OUTPUT", workspace)
        self.assertIn("Cold once · warm reuse", workspace)
        self.assertIn(".studio-workspace", STUDIO_CSS)
        self.assertIn(".workspace-panel", STUDIO_CSS)
        self.assertIn("::-webkit-scrollbar-button", STUDIO_CSS)
        self.assertIn("display: none !important; width: 0 !important; height: 0 !important", STUDIO_CSS)
        self.assertIn("border-radius: 20px", STUDIO_CSS)
        self.assertIn("height: clamp(420px, calc(100vh - 165px), 860px)", STUDIO_CSS)
        self.assertIn("#studio-tabs { margin-top: -34px !important; }", STUDIO_CSS)
        self.assertIn("margin: 0 4px 7px !important", STUDIO_CSS)
        self.assertIn("flex-wrap: nowrap !important", STUDIO_CSS)
        self.assertIn(".workspace-panel > * { flex-shrink: 0", STUDIO_CSS)
        self.assertIn("height: auto; overflow-y: visible", STUDIO_CSS)
        self.assertNotIn(".startup-hint", STUDIO_CSS)
        self.assertNotIn("workspace-steps", workspace)
        self.assertIn("border-radius: 999px", STUDIO_CSS)
        self.assertIn("#media-tabs", STUDIO_CSS)
        self.assertIn('button[role="tab"]::after { display: none', STUDIO_CSS)
        self.assertIn('.tab-container[role="tablist"]::after', STUDIO_CSS)
        self.assertIn("box-shadow: none !important", STUDIO_CSS)
        self.assertIn("#alvenx-header", STUDIO_CSS)
        self.assertIn("background: transparent; backdrop-filter: none", STUDIO_CSS)
        self.assertIn(".workspace-panel .form", STUDIO_CSS)
        self.assertIn("width: 100% !important", STUDIO_CSS)
        self.assertNotIn(".local-badge { font-size: 0; }", STUDIO_CSS)

    def test_run_status_explains_cold_and_warm_model_reuse(self) -> None:
        self.assertIn("Cold start", EMPTY_STATUS_HTML)
        self.assertIn("later runs reuse it", EMPTY_STATUS_HTML)
        result = PlaygroundResult(
            response_text="done",
            latency_ms=100.0,
            model_revision="revision-1",
            backend="qwen3-vl",
            media_kind="image",
            usage={"output_tokens": 12, "max_new_tokens": 64},
        )

        self.assertIn("model is warm for the next run", render_success_status(result))

    def test_hevc_notice_explains_browser_model_compatibility_split(self) -> None:
        info = VideoUploadInfo(
            codec="hevc",
            width=1280,
            height=720,
            duration_seconds=8.9,
            frame_count=267,
            fps=30.0,
            size_bytes=3_266_915,
        )

        notice = render_video_upload_info(info)

        self.assertIn("HEVC/H.265 detected", notice)
        self.assertIn("play only the audio", notice)
        self.assertIn("Local model analysis still uses PyAV", notice)
        self.assertIn("1280×720", notice)
        with patch(
            "openmultimodal_lab.studio_ui.inspect_video_upload",
            return_value=info,
        ):
            self.assertEqual(_inspect_video_upload("video.mp4"), notice)
        self.assertEqual(_inspect_video_upload(None), VIDEO_UPLOAD_GUIDANCE_HTML)

    @unittest.skipUnless(
        importlib.util.find_spec("av") is not None,
        "PyAV is an optional real-model dependency",
    )
    def test_video_upload_inspection_reads_path_free_metadata(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "examples"
            / "assets"
            / "synthetic-video-v1"
            / "count-increase.avi"
        )

        info = inspect_video_upload(source)

        self.assertEqual(info.width, 160)
        self.assertEqual(info.height, 120)
        self.assertGreater(info.size_bytes, 0)
        self.assertNotIn(str(source), repr(info))

    def test_token_limit_is_visible_when_response_may_be_truncated(self) -> None:
        self.assertEqual(PLAYGROUND_UI_DEFAULT_NEW_TOKENS, 512)
        self.assertEqual(PLAYGROUND_MAX_NEW_TOKENS, 1_024)
        self.assertGreater(
            PLAYGROUND_MAX_NEW_TOKENS,
            PLAYGROUND_UI_DEFAULT_NEW_TOKENS,
        )

        result = PlaygroundResult(
            response_text="An incomplete sentence",
            backend="qwen3-vl",
            model_revision="revision-1",
            latency_ms=100.0,
            usage={"output_tokens": 64, "max_new_tokens": 64},
            media_kind="video",
        )

        status = render_success_status(result)
        metrics = render_playground_metrics(result)

        self.assertIn("may be truncated", status)
        self.assertIn("Increase Max new tokens", status)
        self.assertIn("64 / 64 tokens", metrics)

        maxed_result = PlaygroundResult(
            response_text="Still incomplete",
            backend="qwen3-vl",
            model_revision="revision-1",
            latency_ms=100.0,
            usage={
                "output_tokens": PLAYGROUND_MAX_NEW_TOKENS,
                "max_new_tokens": PLAYGROUND_MAX_NEW_TOKENS,
            },
            media_kind="video",
        )
        self.assertIn("split the prompt", render_success_status(maxed_result))

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
            self.assertEqual(len(dependencies), 5)
            self.assertTrue(
                all(
                    item["api_visibility"] == "private"
                    for item in dependencies
                )
            )
            self.assertFalse(app.config["analytics_enabled"])
            tab_labels = [
                item["props"].get("label")
                for item in app.config["components"]
                if item.get("type") == "tabitem"
                and item["props"].get("id")
                in {"workspace", "reports", "about"}
            ]
            self.assertEqual(
                tab_labels[:3],
                ["Workspace", "Reports", "About"],
            )
            clear_button = next(
                item
                for item in app.config["components"]
                if item.get("type") == "button"
                and item["props"].get("value") == "Clear"
            )
            prompt_component = next(
                item
                for item in app.config["components"]
                if item.get("type") == "textbox"
                and item["props"].get("label") == "Prompt"
            )
            clear_event = next(
                item
                for item in dependencies
                if (clear_button["id"], "click") in item["targets"]
            )
            self.assertEqual(len(clear_event["outputs"]), 7)
            self.assertIn(prompt_component["id"], clear_event["outputs"])
            run_button = next(
                item
                for item in app.config["components"]
                if item.get("type") == "button"
                and item["props"].get("value") == "Run locally"
            )
            backend_component = next(
                item
                for item in app.config["components"]
                if item.get("type") == "dropdown"
                and item["props"].get("label") == "Local backend"
            )
            component_order = {
                item["id"]: index
                for index, item in enumerate(app.config["components"])
            }
            self.assertLess(
                component_order[run_button["id"]],
                component_order[backend_component["id"]],
            )
            self.assertLess(
                component_order[clear_button["id"]],
                component_order[backend_component["id"]],
            )
            prompt_prepare_event = next(
                item
                for item in dependencies
                if (run_button["id"], "click") in item["targets"]
            )
            self.assertEqual(
                prompt_prepare_event["outputs"],
                [prompt_component["id"]],
            )
            image_components = [
                item
                for item in app.config["components"]
                if item["props"].get("label")
                == "Image or document screenshot"
            ]
            self.assertEqual(len(image_components), 1)
            self.assertIsNone(image_components[0]["props"].get("format"))
            self.assertIsNone(image_components[0]["props"].get("height"))
            video_components = [
                item
                for item in app.config["components"]
                if item.get("type") == "video"
                and item["props"].get("label") == "Short video"
            ]
            self.assertEqual(len(video_components), 1)
            self.assertTrue(video_components[0]["props"].get("include_audio"))
            self.assertIsNone(video_components[0]["props"].get("height"))
            sliders = {
                item["props"].get("label"): item["props"]
                for item in app.config["components"]
                if item.get("type") == "slider"
            }
            self.assertEqual(
                sliders["Max new tokens"]["minimum"],
                PLAYGROUND_UI_MIN_NEW_TOKENS,
            )
            self.assertEqual(
                sliders["Max new tokens"]["value"],
                PLAYGROUND_UI_DEFAULT_NEW_TOKENS,
            )
            self.assertEqual(
                sliders["Timeout (seconds)"]["minimum"],
                PLAYGROUND_UI_MIN_TIMEOUT_SECONDS,
            )
            self.assertEqual(
                sliders["Timeout (seconds)"]["value"],
                PLAYGROUND_UI_DEFAULT_TIMEOUT_SECONDS,
            )
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

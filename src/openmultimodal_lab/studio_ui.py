"""Optional Gradio interface for Ailumetra Studio.

Gradio is imported lazily so the benchmark core keeps its zero-dependency install.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .studio import (
    BACKEND_LABELS,
    MAX_VIDEO_BYTES,
    PLAYGROUND_MAX_NEW_TOKENS,
    PLAYGROUND_MAX_TIMEOUT_SECONDS,
    PLAYGROUND_PROMPT_MAX_CHARS,
    PLAYGROUND_UI_DEFAULT_NEW_TOKENS,
    PLAYGROUND_UI_DEFAULT_TIMEOUT_SECONDS,
    PLAYGROUND_UI_MIN_NEW_TOKENS,
    PLAYGROUND_UI_MIN_TIMEOUT_SECONDS,
    StudioRuntime,
    inspect_video_upload,
    load_report_view,
    safe_studio_error,
)
from .studio_assets import (
    BRAND_HEADER_HTML,
    CLEARED_STATUS_HTML,
    EASTER_EGG_JS,
    EMPTY_METRICS_HTML,
    EMPTY_REPORT_HTML,
    EMPTY_STATUS_HTML,
    IMAGE_UPLOAD_GUIDANCE_HTML,
    OVERVIEW_HTML,
    REPORT_INTRO_HTML,
    STUDIO_CSS,
    VIDEO_UPLOAD_GUIDANCE_HTML,
    WORKSPACE_INPUT_HEADER_HTML,
    WORKSPACE_OUTPUT_HEADER_HTML,
    render_error_status,
    render_playground_metrics,
    render_report_summary,
    render_success_status,
    render_video_upload_info,
)


LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_PROMPT = "Describe the important visual content and any motion."
REPORT_HEADERS = [
    "Phase",
    "Rep",
    "Task",
    "Status",
    "Score",
    "Latency ms",
    "TTFT ms",
    "Output tok/s",
    "Peak VRAM MiB",
]


class StudioDependencyError(RuntimeError):
    """Raised when the optional Studio dependency is not installed."""


def _import_gradio() -> Any:
    try:
        import gradio as gr
    except (ImportError, OSError) as exc:
        raise StudioDependencyError(
            'Ailumetra Studio requires the optional UI dependencies. Install '
            'them with: python -m pip install -e ".[studio]"'
        ) from exc
    return gr


def _default_prompt_if_empty(prompt: str | None) -> str:
    """Keep a custom prompt or restore the visible Studio default."""

    if not isinstance(prompt, str) or not prompt.strip():
        return DEFAULT_PROMPT
    return prompt


def _run_playground(
    runtime: StudioRuntime,
    backend: str,
    image_path: str | None,
    video_path: str | None,
    prompt: str,
    max_new_tokens: float,
    timeout_seconds: float,
) -> tuple[str, str, str]:
    prompt = _default_prompt_if_empty(prompt)
    try:
        result = runtime.run_playground(
            backend=backend,
            prompt=prompt,
            image_path=image_path,
            video_path=video_path,
            max_new_tokens=int(max_new_tokens),
            timeout_seconds=float(timeout_seconds),
        )
    except Exception as exc:  # The UI boundary must return a path-safe message.
        return (
            "",
            EMPTY_METRICS_HTML,
            render_error_status(safe_studio_error(exc)),
        )
    return (
        result.response_text,
        render_playground_metrics(result),
        render_success_status(result),
    )


def _open_report(path_value: str | None) -> tuple[str, str, list[list[Any]]]:
    if not path_value:
        message = "Select a JSONL run record first."
        return render_error_status(message), "", []
    try:
        view = load_report_view(path_value)
    except Exception as exc:
        return render_error_status(safe_studio_error(exc)), "", []
    return (
        render_report_summary(view),
        view.summary_text,
        [list(row) for row in view.rows],
    )


def _inspect_video_upload(path_value: str | None) -> str:
    if not path_value:
        return VIDEO_UPLOAD_GUIDANCE_HTML
    try:
        info = inspect_video_upload(path_value)
    except Exception as exc:
        return render_error_status(safe_studio_error(exc))
    return render_video_upload_info(info)


def _clear_workspace() -> tuple[
    None,
    None,
    str,
    str,
    str,
    str,
    str,
]:
    """Clear all conversation inputs and outputs without unloading the model."""

    return (
        None,
        None,
        "",
        "",
        EMPTY_METRICS_HTML,
        CLEARED_STATUS_HTML,
        VIDEO_UPLOAD_GUIDANCE_HTML,
    )


def build_app(runtime: StudioRuntime | None = None) -> Any:
    """Build the local Studio without starting a network listener."""

    gr = _import_gradio()
    active_runtime = runtime or StudioRuntime()

    with gr.Blocks(
        title="Ailumetra Studio",
        fill_width=True,
        analytics_enabled=False,
    ) as app:
        gr.HTML(BRAND_HEADER_HTML, elem_id="studio-brand-header")

        with gr.Tabs(selected="workspace", elem_id="studio-tabs"):
            with gr.Tab("Workspace", id="workspace"):
                with gr.Row(elem_classes="studio-workspace"):
                    with gr.Column(
                        scale=6,
                        min_width=360,
                        elem_classes=["workspace-panel", "workspace-input"],
                    ):
                        gr.HTML(WORKSPACE_INPUT_HEADER_HTML)
                        with gr.Tabs(selected="image-input", elem_id="media-tabs"):
                            with gr.Tab("Image / document", id="image-input"):
                                gr.HTML(IMAGE_UPLOAD_GUIDANCE_HTML)
                                image_input = gr.Image(
                                    type="filepath",
                                    format=None,
                                    sources=["upload", "clipboard"],
                                    label="Image or document screenshot",
                                    buttons=["fullscreen"],
                                    elem_id="studio-image-input",
                                    elem_classes="studio-media-input",
                                )
                            with gr.Tab("Short video", id="video-input"):
                                video_guidance = gr.HTML(
                                    VIDEO_UPLOAD_GUIDANCE_HTML
                                )
                                video_input = gr.Video(
                                    sources=["upload"],
                                    label="Short video",
                                    buttons=["fullscreen"],
                                    include_audio=True,
                                    elem_id="studio-video-input",
                                    elem_classes="studio-media-input",
                                )
                        prompt = gr.Textbox(
                            value=DEFAULT_PROMPT,
                            label="Prompt",
                            lines=3,
                            max_lines=8,
                            max_length=PLAYGROUND_PROMPT_MAX_CHARS,
                            placeholder="Ask about visual content, text, layout, or motion...",
                            elem_classes="studio-control",
                        )
                        with gr.Accordion(
                            "Generation controls",
                            open=False,
                            elem_classes="generation-controls",
                        ):
                            with gr.Row():
                                max_tokens = gr.Slider(
                                    minimum=PLAYGROUND_UI_MIN_NEW_TOKENS,
                                    maximum=PLAYGROUND_MAX_NEW_TOKENS,
                                    value=PLAYGROUND_UI_DEFAULT_NEW_TOKENS,
                                    step=16,
                                    precision=0,
                                    label="Max new tokens",
                                    info=(
                                        "Output length limit. Lower values can "
                                        "finish faster but may truncate; 512 is "
                                        "recommended."
                                    ),
                                )
                                timeout = gr.Slider(
                                    minimum=PLAYGROUND_UI_MIN_TIMEOUT_SECONDS,
                                    maximum=PLAYGROUND_MAX_TIMEOUT_SECONDS,
                                    value=PLAYGROUND_UI_DEFAULT_TIMEOUT_SECONDS,
                                    step=30,
                                    precision=0,
                                    label="Timeout (seconds)",
                                    info=(
                                        "Includes first model load. Increase this "
                                        "if a cold run times out."
                                    ),
                                )
                        with gr.Row(elem_classes="workspace-actions"):
                            run_button = gr.Button(
                                "Run locally",
                                variant="primary",
                                elem_id="studio-run-button",
                            )
                            clear_button = gr.Button("Clear", variant="secondary")
                        backend = gr.Dropdown(
                            choices=[
                                (label, name)
                                for name, label in BACKEND_LABELS.items()
                            ],
                            value="qwen3-vl",
                            label="Local backend",
                            filterable=False,
                            elem_classes="studio-control",
                        )
                        status = gr.HTML(EMPTY_STATUS_HTML)

                    with gr.Column(
                        scale=7,
                        min_width=400,
                        elem_classes=["workspace-panel", "workspace-output"],
                    ):
                        gr.HTML(WORKSPACE_OUTPUT_HEADER_HTML)
                        response = gr.Textbox(
                            label="Model response",
                            lines=10,
                            max_lines=30,
                            interactive=False,
                            buttons=["copy"],
                            placeholder="The local model response will appear here.",
                            elem_id="studio-response",
                        )
                        metrics = gr.HTML(EMPTY_METRICS_HTML)

                prepared_prompt = run_button.click(
                    fn=_default_prompt_if_empty,
                    inputs=prompt,
                    outputs=prompt,
                    api_visibility="private",
                    queue=False,
                    show_progress="hidden",
                )
                prepared_prompt.then(
                    fn=lambda *values: _run_playground(active_runtime, *values),
                    inputs=[
                        backend,
                        image_input,
                        video_input,
                        prompt,
                        max_tokens,
                        timeout,
                    ],
                    outputs=[response, metrics, status],
                    api_visibility="private",
                    concurrency_limit=1,
                    concurrency_id="ailumetra-gpu",
                    show_progress="minimal",
                )
                video_input.change(
                    fn=_inspect_video_upload,
                    inputs=video_input,
                    outputs=video_guidance,
                    api_visibility="private",
                    show_progress="hidden",
                    queue=False,
                )
                clear_button.click(
                    fn=_clear_workspace,
                    outputs=[
                        image_input,
                        video_input,
                        prompt,
                        response,
                        metrics,
                        status,
                        video_guidance,
                    ],
                    api_visibility="private",
                    queue=False,
                )

            with gr.Tab("Reports", id="reports"):
                gr.HTML(REPORT_INTRO_HTML)
                with gr.Row(elem_classes="report-loader"):
                    report_file = gr.File(
                        file_types=[".jsonl"],
                        file_count="single",
                        type="filepath",
                        label="Run record (.jsonl)",
                        buttons=[],
                    )
                    report_button = gr.Button(
                        "Open report",
                        variant="primary",
                        elem_id="studio-report-button",
                    )
                report_summary = gr.HTML(EMPTY_REPORT_HTML)
                with gr.Accordion("Text summary", open=False):
                    report_text = gr.Code(
                        language=None,
                        lines=12,
                        interactive=False,
                        show_line_numbers=False,
                        buttons=["copy"],
                    )
                report_table = gr.Dataframe(
                    headers=REPORT_HEADERS,
                    datatype=[
                        "str",
                        "number",
                        "str",
                        "str",
                        "number",
                        "number",
                        "number",
                        "number",
                        "number",
                    ],
                    value=[],
                    interactive=False,
                    wrap=True,
                    show_row_numbers=True,
                    show_search="filter",
                    max_height=520,
                    elem_id="studio-report-table",
                )
                report_button.click(
                    fn=_open_report,
                    inputs=[report_file],
                    outputs=[report_summary, report_text, report_table],
                    api_visibility="private",
                    concurrency_limit=1,
                    show_progress="minimal",
                )

            with gr.Tab("About", id="about"):
                gr.HTML(OVERVIEW_HTML)

    app.queue(api_open=False, max_size=8, default_concurrency_limit=1)
    return app


def launch_studio(
    *,
    host: str = "127.0.0.1",
    port: int = 7860,
    inbrowser: bool = True,
) -> Any:
    """Launch Ailumetra Studio on a loopback address only."""

    if host not in LOOPBACK_HOSTS:
        raise ValueError("Ailumetra Studio only accepts a loopback host")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")

    app = build_app()
    return app.launch(
        server_name=host,
        server_port=port,
        inbrowser=inbrowser,
        share=False,
        show_error=False,
        allowed_paths=[],
        max_file_size=MAX_VIDEO_BYTES,
        enable_monitoring=False,
        strict_cors=True,
        footer_links=[],
        theme="base",
        css=STUDIO_CSS,
        js=EASTER_EGG_JS,
    )

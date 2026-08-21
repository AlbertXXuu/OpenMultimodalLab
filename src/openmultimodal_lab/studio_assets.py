"""Brand copy, accessible HTML, CSS, and interactions for AlvenX Studio."""

from __future__ import annotations

import base64
import hashlib
from html import escape
from importlib.resources import files
from typing import Any

from .studio import (
    PLAYGROUND_MAX_NEW_TOKENS,
    PlaygroundResult,
    ReportView,
    VideoUploadInfo,
)


INSTRUMENT_SANS_REVISION = "7fa22308a3d0c94ee2b3cd537a1196b65db34a3e"
INSTRUMENT_SANS_SHA256 = (
    "aa72922aafcc0dc18f36ec1d805b0212057dabe8b9d5b8b57f67035aea1b826d"
)
ALVENX_WORDMARK_SHA256 = (
    "a17e802a71b30b04a26e5b0da6c1adda93b0705463d237d142f50dac4ed40192"
)


def _instrument_sans_base64() -> str:
    payload = (
        files("openmultimodal_lab")
        .joinpath("assets/fonts/InstrumentSans-wdth-wght.woff2.b64")
        .read_text(encoding="ascii")
    )
    encoded = "".join(payload.split())
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("The bundled Instrument Sans font is corrupt.") from exc
    if (
        not decoded.startswith(b"wOF2")
        or hashlib.sha256(decoded).hexdigest() != INSTRUMENT_SANS_SHA256
    ):
        raise RuntimeError("The bundled Instrument Sans font failed integrity check.")
    return encoded


def _alvenx_wordmark_base64() -> str:
    payload = (
        files("openmultimodal_lab")
        .joinpath("assets/brand/alvenx-wordmark.svg.b64")
        .read_text(encoding="ascii")
    )
    encoded = "".join(payload.split())
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("The bundled AlvenX wordmark is corrupt.") from exc
    if (
        not decoded.lstrip().startswith(b"<svg")
        or hashlib.sha256(decoded).hexdigest() != ALVENX_WORDMARK_SHA256
    ):
        raise RuntimeError("The bundled AlvenX wordmark failed integrity check.")
    return encoded


_INSTRUMENT_SANS_FONT_FACE = f"""
@font-face {{
  font-family: "Instrument Sans";
  src: url("data:font/woff2;base64,{_instrument_sans_base64()}") format("woff2");
  font-style: normal;
  font-weight: 400 700;
  font-stretch: 75% 100%;
  font-display: swap;
}}
"""


BRAND_HEADER_HTML = f"""
<header id="alvenx-header" class="studio-shell">
  <button id="alvenx-wordmark-button" class="brand-wordmark" type="button"
          aria-label="AlvenX wordmark" title="AlvenX">
    <img class="brand-wordmark-image"
         src="data:image/svg+xml;base64,{_alvenx_wordmark_base64()}"
         alt="" aria-hidden="true">
  </button>
  <div class="header-tagline">Measure multimodal AI. See clearly.</div>
  <div class="local-badge"><span aria-hidden="true"></span> Local only</div>
</header>
<section id="alonica-signal" class="developer-signal" role="dialog"
         aria-modal="true" aria-labelledby="alonica-title" hidden>
  <button id="alonica-close" type="button" aria-label="Close developer signal">×</button>
  <div class="signal-kicker">SIGNAL DISCOVERED</div>
  <h2 id="alonica-title">Developer // ALONICA</h2>
  <p>Build locally. Measure honestly.</p>
  <code>AlvenX Studio · signal 01</code>
</section>
""".strip()


OVERVIEW_HTML = """
<main class="overview-stack studio-shell">
  <section class="hero-panel">
    <div class="eyebrow">LOCAL-FIRST MULTIMODAL EVALUATION</div>
    <h1>From media to evidence,<br><span>on hardware you own.</span></h1>
    <p>AlvenX is the product layer for OpenMultimodalLab: run real vision-language
       models locally, inspect honest performance signals, and rebuild the report from
       preserved records.</p>
    <div class="hero-pills" aria-label="Project capabilities">
      <span>Images</span><span>Document screenshots</span><span>Short video</span>
      <span>Versioned tasks</span>
    </div>
  </section>

  <section class="proof-grid" aria-label="Version 1.0 evidence">
    <article><strong>102</strong><span>human-checked tasks</span></article>
    <article><strong>2</strong><span>real open models</span></article>
    <article><strong>612</strong><span>measured attempts</span></article>
    <article><strong>8 GB</strong><span>consumer GPU profile</span></article>
  </section>

  <section class="comparison-panel">
    <div class="section-heading">
      <div><span class="eyebrow">PRESERVED V1.0.0 EVIDENCE</span>
        <h2>One task grid. Two hardware trade-offs.</h2></div>
      <span class="evidence-pill">1 warm-up · 3 repetitions</span>
    </div>
    <div class="model-lane">
      <div class="model-title"><span class="model-dot qwen"></span>
        <div><strong>Qwen3-VL-2B</strong><small>Higher aggregate quality</small></div>
      </div>
      <div class="score-cell"><span>Mean score</span><strong>0.784</strong>
        <div class="score-track"><i style="width:78.4%"></i></div></div>
      <div class="number-cell"><span>Median TTFT</span><strong>120.5 ms</strong></div>
      <div class="number-cell"><span>Peak VRAM</span><strong>4,180.5 MiB</strong></div>
      <div class="status-cell success">306 / 306</div>
    </div>
    <div class="model-lane">
      <div class="model-title"><span class="model-dot smol"></span>
        <div><strong>SmolVLM2-500M</strong><small>Lower memory footprint</small></div>
      </div>
      <div class="score-cell"><span>Mean score</span><strong>0.690</strong>
        <div class="score-track"><i style="width:69%"></i></div></div>
      <div class="number-cell"><span>Median TTFT</span><strong>260.0 ms</strong></div>
      <div class="number-cell"><span>Peak VRAM</span><strong>1,265.3 MiB</strong></div>
      <div class="status-cell success">306 / 306</div>
    </div>
    <p class="evidence-note">Recorded on one RTX 4060 Laptop GPU. Token throughput
      is not treated as cross-family semantic equivalence. This panel reports preserved
      evidence; it does not rerun either model.</p>
  </section>

  <section class="workflow-grid" aria-label="Studio workflow">
    <article><span>01</span><h3>Bring one input</h3>
      <p>Upload an image, document screenshot, or short video. It stays on this machine.</p></article>
    <article><span>02</span><h3>Run one local model</h3>
      <p>Use the pinned Qwen3-VL or SmolVLM2 backend through the existing adapter contract.</p></article>
    <article><span>03</span><h3>Inspect the evidence</h3>
      <p>Read TTFT, latency, output throughput, peak GPU memory, and durable run reports.</p></article>
  </section>
</main>
""".strip()


WORKSPACE_INPUT_HEADER_HTML = """
<header class="workspace-panel-header">
  <div><span class="panel-index">01</span><span class="eyebrow">INPUT</span>
    <h3>Configure a local run</h3></div>
  <span class="panel-note">Cold once · warm reuse</span>
</header>
""".strip()


WORKSPACE_OUTPUT_HEADER_HTML = """
<header class="workspace-panel-header">
  <div><span class="panel-index">02</span><span class="eyebrow">OUTPUT</span>
    <h3>Response and runtime evidence</h3></div>
  <span class="panel-note">Unscored preview</span>
</header>
""".strip()


IMAGE_UPLOAD_GUIDANCE_HTML = """
<div class="media-guidance" role="note">
  <strong>Image boundary</strong>
  <span>Up to 25 MiB · aspect-safe preview · never crops the evidence.</span>
</div>
""".strip()


VIDEO_UPLOAD_GUIDANCE_HTML = """
<div class="media-guidance" role="note">
  <strong>Short-video boundary</strong>
  <span>Up to 50 MiB · 60 seconds · 3,600 frames · 4K. Prefer H.264 MP4 for moving
        preview; H.265/HEVC may show a still frame but remains model-readable.</span>
</div>
""".strip()


def render_video_upload_info(info: VideoUploadInfo) -> str:
    """Explain the difference between browser playback and model decoding."""

    codec = info.codec.casefold()
    if codec in {"hevc", "h265"}:
        status_class = "warning"
        title = "HEVC/H.265 detected · model-compatible"
        message = (
            "Some browsers play only the audio or hold one frame. Local model "
            "analysis still uses PyAV; use H.264 MP4 for portable moving preview."
        )
    elif codec in {"h264", "avc", "avc1"}:
        status_class = "compatible"
        title = "H.264 detected · portable browser preview"
        message = "The original upload remains the source used by the local model."
    else:
        status_class = "neutral"
        title = f"{info.codec.upper() or 'UNKNOWN'} video detected"
        message = (
            "Browser playback depends on installed codecs; local model validation "
            "runs separately."
        )

    duration = (
        f"{info.duration_seconds:.1f} s"
        if info.duration_seconds is not None
        else "duration n/a"
    )
    frames = (
        f"{info.frame_count:,} frames"
        if info.frame_count is not None
        else "frame count n/a"
    )
    fps = f"{info.fps:.1f} FPS" if info.fps is not None else "FPS n/a"
    size_mib = info.size_bytes / (1024 * 1024)
    return (
        f'<div class="media-guidance {status_class}" role="status">'
        f"<strong>{escape(title)}</strong>"
        f"<span>{escape(message)}</span>"
        '<small class="media-facts">'
        f"{info.width}×{info.height} · {escape(duration)} · "
        f"{escape(frames)} · {escape(fps)} · {size_mib:.2f} MiB"
        "</small></div>"
    )


REPORT_INTRO_HTML = """
<section class="tab-intro">
  <div><span class="eyebrow">REPORT EXPLORER</span><h2>Open durable run evidence</h2></div>
  <p>Load a JSONL produced by <code>oml run</code>. The Studio does not rewrite it.</p>
</section>
""".strip()


EMPTY_METRICS_HTML = """
<section class="metric-panel empty-state">
  <span class="eyebrow">LIVE METRICS</span>
  <h3>Waiting for a local run</h3>
  <p>TTFT, throughput, latency, and peak GPU memory will appear here when the backend
     reports them.</p>
</section>
""".strip()


EMPTY_STATUS_HTML = """
<div class="run-status idle"><span></span><strong>Cold start</strong> · the first run
loads the selected model; later runs reuse it</div>
""".strip()


CLEARED_STATUS_HTML = """
<div class="run-status idle"><span></span>Cleared · inputs reset; any loaded model
remains warm</div>
""".strip()


EMPTY_REPORT_HTML = """
<section class="metric-panel empty-state">
  <span class="eyebrow">RUN SUMMARY</span>
  <h3>No report loaded</h3>
  <p>Select a JSONL run record to inspect protocol status and measurements.</p>
</section>
""".strip()


def _metric_value(value: object, suffix: str, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{numeric:,.{digits}f}{suffix}"


def _usage_integer(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _metric_card(label: str, value: str, note: str = "") -> str:
    note_html = f"<small>{escape(note)}</small>" if note else ""
    return (
        '<article class="live-card">'
        f"<span>{escape(label)}</span><strong>{escape(value)}</strong>{note_html}"
        "</article>"
    )


def render_playground_metrics(result: PlaygroundResult) -> str:
    usage = result.usage
    cards = [
        _metric_card("Wall latency", _metric_value(result.latency_ms, " ms")),
        _metric_card("TTFT", _metric_value(usage.get("ttft_ms"), " ms")),
        _metric_card(
            "Output throughput",
            _metric_value(usage.get("output_tokens_per_second"), " tok/s"),
        ),
        _metric_card(
            "Peak GPU memory",
            _metric_value(usage.get("peak_gpu_memory_mb"), " MiB"),
        ),
    ]
    model_load = _metric_value(usage.get("model_load_ms"), " ms")
    output_tokens = _usage_integer(usage.get("output_tokens"))
    token_limit = _usage_integer(usage.get("max_new_tokens"))
    output_length = (
        f"{output_tokens} / {token_limit} tokens"
        if output_tokens is not None and token_limit is not None
        else "n/a"
    )
    backend = escape(result.backend)
    revision = escape(result.model_revision[:12])
    return (
        '<section class="metric-panel">'
        '<div class="panel-top"><span class="eyebrow">LIVE METRICS</span>'
        '<span class="unscored-pill">UNSCORED</span></div>'
        f'<div class="live-grid">{"".join(cards)}</div>'
        '<div class="runtime-foot">'
        f"<span>Backend <strong>{backend}</strong></span>"
        f"<span>Revision <code>{revision}</code></span>"
        f"<span>Model load <strong>{escape(model_load)}</strong></span>"
        f"<span>Output <strong>{escape(output_length)}</strong></span>"
        "</div></section>"
    )


def render_success_status(result: PlaygroundResult) -> str:
    output_tokens = _usage_integer(result.usage.get("output_tokens"))
    token_limit = _usage_integer(result.usage.get("max_new_tokens"))
    if (
        output_tokens is not None
        and token_limit is not None
        and output_tokens >= token_limit
    ):
        next_step = (
            "Increase Max new tokens and run again."
            if token_limit < PLAYGROUND_MAX_NEW_TOKENS
            else "Ask for a shorter answer or split the prompt into smaller questions."
        )
        return (
            '<div class="run-status warning"><span></span>'
            f"Completed, but reached the {token_limit}-token output limit; "
            f"the final sentence may be truncated. The model remains warm. {next_step}"
            "</div>"
        )
    return (
        '<div class="run-status success"><span></span>'
        f"Completed locally · <strong>model is warm for the next run</strong> · "
        f"{escape(result.media_kind)} · no quality score assigned"
        "</div>"
    )


def render_error_status(message: str) -> str:
    return (
        '<div class="run-status error"><span></span>'
        f"{escape(message)}"
        "</div>"
    )


def render_report_summary(view: ReportView) -> str:
    summary = view.summary
    formal = bool(summary.get("formal_performance_run"))
    protocol_label = "FORMAL PROTOCOL" if formal else "NON-FORMAL RUN"
    protocol_class = "formal" if formal else "informal"
    cards = [
        _metric_card(
            "Success rate",
            _metric_value(float(summary.get("success_rate", 0)) * 100, "%"),
        ),
        _metric_card("Mean score", _metric_value(summary.get("mean_score"), "", 3)),
        _metric_card(
            "Median TTFT", _metric_value(summary.get("median_ttft_ms"), " ms")
        ),
        _metric_card(
            "Peak GPU memory",
            _metric_value(summary.get("peak_gpu_memory_mb"), " MiB"),
        ),
    ]
    return (
        '<section class="metric-panel">'
        '<div class="panel-top"><div>'
        '<span class="eyebrow">RUN SUMMARY</span>'
        f"<h3>{escape(view.filename)}</h3></div>"
        f'<span class="protocol-pill {protocol_class}">{protocol_label}</span></div>'
        f'<div class="live-grid">{"".join(cards)}</div>'
        '<div class="runtime-foot">'
        f"<span>Records <strong>{int(summary.get('total_records', 0))}</strong></span>"
        f"<span>Unique tasks <strong>{int(summary.get('unique_tasks', 0))}</strong></span>"
        f"<span>Repetitions <strong>{int(summary.get('repetitions', 0))}</strong></span>"
        f"<span>Failures <strong>{escape(str(summary.get('failures', {})))}</strong></span>"
        "</div></section>"
    )


STUDIO_CSS = (_INSTRUMENT_SANS_FONT_FACE + """
:root {
  --alx-font-sans: "Instrument Sans", "Microsoft YaHei UI", "PingFang SC", Arial, sans-serif;
  --alx-font-mono: "Cascadia Code", "SFMono-Regular", Consolas, monospace;
  --alx-bg: #eef6ff;
  --alx-panel: rgb(255 255 255 / 78%);
  --alx-panel-strong: rgb(255 255 255 / 90%);
  --alx-panel-2: rgb(248 251 255 / 74%);
  --alx-border: rgb(71 85 105 / 14%);
  --alx-text: #0b1731;
  --alx-reading: #334155;
  --alx-muted: #52647a;
  --alx-blue: #2563eb;
  --alx-blue-strong: #1d4ed8;
  --alx-blue-soft: rgb(219 234 254 / 72%);
  --alx-indigo: #4f46e5;
  --alx-violet: #7c3aed;
  --alx-red: #dc2626;
  --alx-amber: #b45309;
  --alx-glass-fill: rgb(255 255 255 / 28%);
  --alx-glass-fill-hover: rgb(255 255 255 / 35%);
  --alx-glass-edge: rgb(255 255 255 / 68%);
  --alx-glass-highlight: rgb(255 255 255 / 72%);
  --alx-glass-shadow: 0 22px 60px rgb(71 105 148 / 15%);
  --alx-glass-blur: 24px;
  --alx-radius-shell: 22px;
  --alx-radius-card: 20px;
  --alx-radius-control: 14px;
  --alx-radius-inset: 12px;
  --alx-radius-pill: 999px;
  --alx-ease-fluid: cubic-bezier(0.22, 1, 0.36, 1);
}
html, body {
  color-scheme: light !important;
  font-family: var(--alx-font-sans) !important;
  font-feature-settings: "ss01" 1, "ss02" 1;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}
body {
  background:
    radial-gradient(circle at 10% 0%, rgb(255 255 255 / 96%), transparent 34%),
    radial-gradient(circle at 92% 7%, rgb(147 197 253 / 22%), transparent 38%),
    radial-gradient(circle at 8% 96%, rgb(124 58 237 / 8%), transparent 36%),
    linear-gradient(145deg, #fbfdff 0%, #f1f7ff 49%, #e7f1ff 100%) !important;
  background-attachment: fixed !important;
  color: var(--alx-text) !important;
}
.gradio-container {
  background: transparent !important;
  color: var(--alx-text) !important;
}
.gradio-container, .gradio-container .prose, .gradio-container button,
.gradio-container input, .gradio-container textarea, .gradio-container select,
.gradio-container table {
  font-family: var(--alx-font-sans) !important;
  font-feature-settings: "ss01" 1, "ss02" 1;
  font-synthesis: none;
}
.gradio-container {
  width: 100% !important; max-width: 1560px !important; margin: 0 auto !important;
  padding-inline: 18px !important;
  --body-background-fill: var(--alx-bg);
  --body-text-color: var(--alx-text);
  --body-text-color-subdued: var(--alx-muted);
  --background-fill-primary: var(--alx-panel);
  --background-fill-secondary: var(--alx-panel-2);
  --block-background-fill: var(--alx-panel);
  --block-label-background-fill: var(--alx-panel);
  --block-label-text-color: #334155;
  --block-title-text-color: var(--alx-text);
  --input-background-fill: rgb(255 255 255 / 84%);
  --input-border-color: rgba(15,23,42,.16);
  --input-placeholder-color: #64748b;
  --border-color-primary: rgba(15,23,42,.12);
  --border-color-accent: var(--alx-blue);
  --button-secondary-background-fill: rgb(255 255 255 / 48%);
  --button-secondary-background-fill-hover: rgb(255 255 255 / 66%);
  --button-secondary-text-color: #334155;
  --button-secondary-text-color-hover: #0b1731;
  --table-odd-background-fill: rgb(255 255 255 / 88%);
  --table-even-background-fill: rgb(248 251 255 / 86%);
  --shadow-drop: 0 1px 2px rgba(15,23,42,.06);
  --shadow-drop-lg: 0 14px 38px rgba(15,23,42,.09);
}
.gradio-container .prose, .hero-panel h1,
.section-heading h2, .tab-intro h2, .comparison-panel strong,
.workflow-grid h3, .metric-panel h3 { color: var(--alx-text) !important; }
.gradio-container button[role="tab"] {
  color: #64748b !important; background: transparent !important;
  border: 1px solid transparent !important;
  transition: color 360ms var(--alx-ease-fluid), background-color 360ms var(--alx-ease-fluid),
    border-color 360ms var(--alx-ease-fluid), box-shadow 360ms var(--alx-ease-fluid);
}
.gradio-container button[role="tab"][aria-selected="true"] {
  color: var(--alx-blue) !important;
}
.gradio-container button[role="tab"]:focus-visible {
  outline: 3px solid rgb(37 99 235 / 42%) !important;
  outline-offset: 2px !important;
}
#studio-tabs > .tab-nav, #studio-tabs > div:first-child {
  border: 0 !important; border-radius: 0;
  background: transparent; padding: 0;
  margin: 0 4px 7px !important; min-height: 34px;
  box-shadow: none !important;
}
#studio-tabs { margin-top: -34px !important; }
#studio-tabs button[role="tab"] {
  border-radius: var(--alx-radius-pill) !important; min-height: 34px;
  padding: 6px 16px !important;
}
#studio-tabs button[role="tab"]::after { display: none !important; }
#studio-tabs > .tab-wrapper::after,
#studio-tabs > .tab-wrapper::before { display: none !important; }
#studio-tabs > .tab-wrapper > .tab-container[role="tablist"]::after {
  display: none !important;
}
#studio-tabs button[role="tab"][aria-selected="true"] {
  border-color: var(--alx-glass-edge) !important;
  background: var(--alx-glass-fill) !important;
  box-shadow: inset 0 1px 0 var(--alx-glass-highlight), 0 12px 32px rgb(71 105 148 / 9%);
  backdrop-filter: blur(18px) saturate(138%);
  -webkit-backdrop-filter: blur(18px) saturate(138%);
}
#media-tabs > .tab-nav, #media-tabs > div:first-child {
  width: 100%; margin: 0 0 8px !important; padding: 3px;
  border: 1px solid var(--alx-glass-edge); border-radius: 16px;
  background: rgb(255 255 255 / 44%); box-shadow: inset 0 1px 0 rgb(255 255 255 / 54%);
}
#media-tabs button[role="tab"] {
  min-height: 32px; padding: 5px 12px !important;
  border-radius: var(--alx-radius-inset) !important;
}
.studio-shell { margin-left: auto; margin-right: auto; }
#studio-brand-header { margin: 0 !important; padding: 0 !important; }
#alvenx-header {
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
  margin: 2px 4px 4px; padding: 4px 8px;
  border: 0; border-radius: 0;
  background: transparent; backdrop-filter: none;
  box-shadow: none;
}
.brand-wordmark { display: inline-flex; align-items: center;
  width: max-content; padding: 2px 4px; border: 0; border-radius: var(--alx-radius-control);
  background: transparent; color: inherit; cursor: pointer;
  font-family: var(--alx-font-sans); }
.brand-wordmark:focus-visible { outline: 2px solid var(--alx-blue); outline-offset: 3px; }
.brand-wordmark-image { display: block; width: clamp(150px,13.5vw,178px); height: auto; }
.header-tagline { color: var(--alx-reading); font-size: 13px; letter-spacing: .02em; }
.local-badge { justify-self: end; display: inline-flex; align-items: center; gap: 7px;
  color: var(--alx-blue-strong); font-size: 12px; font-weight: 650; padding: 7px 10px;
  border: 1px solid var(--alx-glass-edge); background: var(--alx-glass-fill);
  border-radius: var(--alx-radius-pill); white-space: nowrap;
  box-shadow: inset 0 1px 0 var(--alx-glass-highlight); backdrop-filter: blur(18px) saturate(138%);
  -webkit-backdrop-filter: blur(18px) saturate(138%); }
.local-badge span, .run-status > span { width: 7px; height: 7px; border-radius: 50%;
  background: var(--alx-blue); box-shadow: 0 0 10px rgba(37,99,235,.32); }
.developer-signal { position: fixed; z-index: 99999; top: 50%; left: 50%;
  transform: translate(-50%,-50%); width: min(440px, calc(100vw - 36px));
  padding: 30px; border: 1px solid var(--alx-glass-edge); border-radius: 22px;
  background: var(--alx-panel-strong); color: var(--alx-text); box-shadow: 0 30px 100px rgba(15,23,42,.18);
  backdrop-filter: blur(var(--alx-glass-blur)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--alx-glass-blur)) saturate(140%);
  font-family: var(--alx-font-sans); }
.developer-signal[hidden] { display: none; }
.developer-signal:before { content: ""; position: absolute; inset: 0; pointer-events: none;
  border-radius: inherit; background: rgba(37,99,235,.018); }
.developer-signal button { position: absolute; top: 10px; right: 12px; width: 32px;
  border: 0; background: transparent; color: var(--alx-muted); font-size: 24px; cursor: pointer; }
.signal-kicker, .eyebrow { color: var(--alx-blue); font-size: 10px; font-weight: 700;
  letter-spacing: .18em; }
.developer-signal h2 { margin: 13px 0 4px; font-size: 21px; }
.developer-signal p { color: var(--alx-reading); margin: 0 0 18px; }
.developer-signal code { color: var(--alx-violet); font-family: var(--alx-font-mono); }
.overview-stack { display: grid; gap: 14px; padding: 4px; }
.hero-panel, .comparison-panel, .metric-panel, .workflow-grid article, .proof-grid article {
  border: 1px solid rgb(255 255 255 / 76%); background: var(--alx-panel-strong);
  box-shadow: 0 16px 42px rgb(71 105 148 / 9%); }
.hero-panel { position: relative; overflow: hidden; min-height: 330px; padding: 58px 52px;
  border-radius: 22px; display: flex; flex-direction: column; justify-content: center; }
.hero-panel:after { content: "A"; position: absolute; right: 4%; top: -25%; font-size: 400px;
  font-weight: 700; font-stretch: 78%; color: transparent;
  -webkit-text-stroke: 1px rgba(37,99,235,.09);
  transform: rotate(5deg); pointer-events: none; }
.hero-panel h1 { margin: 15px 0 16px; max-width: 830px; font-size: clamp(38px,6vw,72px);
  line-height: .98; letter-spacing: -.058em; font-weight: 680; font-stretch: 94%; }
.hero-panel h1 span {
  background-image: linear-gradient(100deg,var(--alx-blue) 0%,var(--alx-indigo) 58%,
    var(--alx-violet) 100%) !important;
  -webkit-background-clip: text !important; background-clip: text !important;
  color: transparent !important;
}
.hero-panel > p { max-width: 720px; color: var(--alx-reading); line-height: 1.65; font-size: 15px; }
.hero-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.hero-pills span, .evidence-pill { border: 1px solid var(--alx-border); color: #334155;
  background: var(--alx-panel-2); border-radius: var(--alx-radius-pill); padding: 7px 10px; font-size: 11px; }
.proof-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; }
.proof-grid article { padding: 23px; border-radius: 16px; }
.proof-grid strong { display: block; font-size: 30px; letter-spacing: -.04em; }
.proof-grid span { color: var(--alx-muted); font-size: 12px; }
.comparison-panel { padding: 28px; border-radius: 20px; }
.section-heading, .panel-top { display: flex; justify-content: space-between; align-items: center;
  gap: 18px; margin-bottom: 20px; }
.section-heading h2, .tab-intro h2 { margin: 7px 0 0; font-size: 25px;
  letter-spacing: -.04em; font-weight: 650; font-stretch: 95%; }
.tab-intro h2, .metric-panel h3 {
  font-family: var(--alx-font-sans); font-weight: 650; font-synthesis: none;
}
.model-lane { display: grid; grid-template-columns: minmax(210px,1.5fr) minmax(160px,1fr)
  minmax(120px,.8fr) minmax(135px,.9fr) 92px; gap: 20px; align-items: center;
  padding: 20px 4px; border-top: 1px solid var(--alx-border); }
.model-title { display: flex; align-items: center; gap: 12px; }
.model-title strong { display: block; font-size: 15px; }
.model-title small, .score-cell span, .number-cell span { display: block; color: var(--alx-muted);
  font-size: 10px; margin-bottom: 4px; }
.model-dot { width: 10px; height: 10px; border-radius: 50%; }
.model-dot.qwen { background: var(--alx-violet); box-shadow: 0 0 16px rgba(167,139,250,.65); }
.model-dot.smol { background: var(--alx-blue); box-shadow: 0 0 16px rgba(96,165,250,.65); }
.score-cell strong, .number-cell strong { font-family: var(--alx-font-sans);
  font-feature-settings: "ss02" 1, "tnum" 1; font-variant-numeric: tabular-nums;
  font-size: 15px; font-weight: 620; }
.score-track { height: 3px; margin-top: 7px; background: #e2e8f0; border-radius: 10px; overflow: hidden; }
.score-track i { display: block; height: 100%; background: var(--alx-blue); }
.status-cell { justify-self: end; font-family: var(--alx-font-sans);
  font-feature-settings: "ss02" 1, "tnum" 1; font-variant-numeric: tabular-nums;
  font-size: 10px; font-weight: 620; padding: 6px 8px; border-radius: 7px; }
.status-cell.success { color: var(--alx-blue-strong); background: var(--alx-blue-soft); }
.evidence-note { margin: 15px 0 0; color: #64748b; font-size: 11px; line-height: 1.6; }
.workflow-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; background: transparent;
  border: 0; box-shadow: none; }
.workflow-grid article { border-radius: 16px; padding: 25px; }
.workflow-grid article > span { color: var(--alx-blue); font-family: var(--alx-font-sans);
  font-variant-numeric: tabular-nums; font-size: 11px; font-weight: 650; }
.workflow-grid h3 { margin: 16px 0 8px; font-size: 16px; }
.workflow-grid p { margin: 0; color: var(--alx-muted); font-size: 12px; line-height: 1.6; }
.tab-intro { display: flex; align-items: end; justify-content: space-between; gap: 16px;
  padding: 6px 6px 7px; }
.tab-intro p { color: var(--alx-muted); font-size: 12px; }
.studio-workspace { align-items: stretch !important; gap: 14px !important; }
.gradio-container::-webkit-scrollbar-button,
.gradio-container *::-webkit-scrollbar-button {
  -webkit-appearance: none; display: none !important; width: 0 !important; height: 0 !important;
}
.workspace-panel { min-width: 0; padding: 16px !important; border: 1px solid var(--alx-border);
  height: clamp(420px, calc(100vh - 165px), 860px); overflow-y: auto;
  flex-wrap: nowrap !important;
  scrollbar-width: thin; scrollbar-color: #cbd5e1 transparent;
  border-radius: 20px; background: var(--alx-panel-strong); box-shadow: 0 14px 38px rgb(71 105 148 / 9%); }
.workspace-panel > * { flex-shrink: 0 !important; }
.workspace-panel-header { display: flex; justify-content: space-between; align-items: flex-start;
  gap: 14px; min-height: 52px; margin: 0 0 12px; padding-bottom: 12px;
  border-bottom: 1px solid var(--alx-border); }
.workspace-panel-header > div { display: grid; grid-template-columns: auto 1fr; align-items: center;
  gap: 0 9px; }
.workspace-panel-header h3 { grid-column: 1 / -1; margin: 8px 0 0; color: var(--alx-text);
  font-size: 18px; font-weight: 650; font-stretch: 95%; letter-spacing: -.025em; }
.panel-index { display: inline-grid; place-items: center; width: 24px; height: 24px;
  border-radius: 8px; background: var(--alx-blue-soft); color: var(--alx-blue-strong);
  font-size: 10px; font-weight: 700; font-variant-numeric: tabular-nums; }
.panel-note { padding: 6px 8px; border-radius: 8px; background: var(--alx-panel-2);
  color: #64748b; font-size: 9px; font-weight: 650; letter-spacing: .05em;
  text-transform: uppercase; white-space: nowrap; }
.generation-controls { border: 1px solid var(--alx-border) !important; border-radius: 12px !important;
  background: var(--alx-panel-2) !important; }
.workspace-actions { align-items: center !important; }
.workspace-actions button { border-radius: var(--alx-radius-pill) !important; }
.workspace-output #studio-response textarea { min-height: 300px !important; line-height: 1.62; }
.workspace-output .metric-panel { margin-top: 4px; }
.media-guidance { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 9px;
  margin: 2px 0 9px; padding: 9px 11px; border: 1px solid rgba(37,99,235,.14);
  border-radius: 10px; background: var(--alx-panel-2); color: var(--alx-muted); font-size: 10px;
  line-height: 1.55; }
.media-guidance strong { color: #334155; font-size: 10px; white-space: nowrap; }
.media-guidance small.media-facts { flex-basis: 100%; color: #64748b;
  font-family: var(--alx-font-mono); font-size: 9px; }
.media-guidance.warning { border-color: rgba(180,83,9,.25); background: #fffbeb; }
.media-guidance.warning strong { color: #92400e; }
.media-guidance.compatible { border-color: rgba(37,99,235,.2); background: var(--alx-blue-soft); }
.media-guidance.compatible strong { color: var(--alx-blue-strong); }
.studio-media-input { height: auto !important; min-height: 210px;
  max-height: none !important; overflow: visible !important;
  background: var(--alx-panel-2) !important;
  border-radius: 14px !important; }
#studio-image-input .image-container, #studio-image-input .image-frame,
#studio-video-input .video-container, #studio-video-input .wrap {
  height: auto !important; min-height: 210px; max-height: 360px !important;
}
.studio-media-input img, .studio-media-input video {
  display: block; width: 100% !important; max-width: 100% !important;
  height: auto !important;
  min-height: 0 !important; max-height: 360px !important;
  margin: auto; object-fit: contain !important; background: var(--alx-panel-2);
}
.metric-panel { padding: 18px; border-radius: var(--alx-radius-card); min-height: 190px; }
.metric-panel h3 { margin: 8px 0 0; font-size: 17px; letter-spacing: -.018em; }
.empty-state { display: flex; flex-direction: column; justify-content: center; }
.empty-state p { color: var(--alx-muted); max-width: 450px; line-height: 1.6; font-size: 12px; }
.live-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 10px; }
.live-card { padding: 16px; border: 1px solid var(--alx-border); border-radius: 12px;
  background: var(--alx-panel-2); }
.live-card span { display: block; color: var(--alx-muted); font-size: 10px; margin-bottom: 7px; }
.live-card strong { font-family: var(--alx-font-sans);
  font-feature-settings: "ss02" 1, "tnum" 1; font-variant-numeric: tabular-nums;
  font-size: 17px; font-weight: 650; letter-spacing: -.025em; }
.live-card small { display: block; margin-top: 6px; color: #64748b; font-size: 9px; }
.unscored-pill, .protocol-pill { padding: 6px 8px; border-radius: 7px; font-size: 9px;
  font-weight: 700; letter-spacing: .12em; }
.unscored-pill, .protocol-pill.informal { color: #92400e; background: #fffbeb; }
.protocol-pill.formal { color: var(--alx-blue-strong); background: var(--alx-blue-soft); }
.runtime-foot { display: flex; flex-wrap: wrap; gap: 14px 20px; border-top: 1px solid var(--alx-border);
  margin-top: 18px; padding-top: 14px; color: var(--alx-muted); font-size: 10px; }
.runtime-foot strong, .runtime-foot code { color: #334155; }
.run-status { display: flex; align-items: center; gap: 8px; padding: 10px 13px;
  border: 1px solid var(--alx-border); border-radius: 11px; color: var(--alx-muted); font-size: 11px; }
.run-status strong { color: #334155; font-weight: 650; }
.run-status.idle > span { background: #64748b; box-shadow: none; }
.run-status.error { color: #b91c1c; border-color: rgba(220,38,38,.2); background: #fef2f2; }
.run-status.error > span { background: var(--alx-red); box-shadow: 0 0 10px rgba(220,38,38,.32); }
.run-status.warning { color: #92400e; border-color: rgba(180,83,9,.24); background: #fffbeb; }
.run-status.warning > span { background: var(--alx-amber); box-shadow: 0 0 10px rgba(180,83,9,.25); }
.gradio-container .form, .gradio-container .block { border-color: var(--alx-border) !important; }
.workspace-panel .form, .workspace-panel .block {
  border-radius: var(--alx-radius-control) !important;
}
.gradio-container button.primary {
  position: relative; isolation: isolate; overflow: hidden; min-height: 46px;
  border: 1px solid var(--alx-glass-edge) !important;
  border-radius: var(--alx-radius-pill) !important;
  background-color: var(--alx-glass-fill) !important;
  background-image: radial-gradient(circle at 24% -12%, rgb(255 255 255 / 76%), transparent 43%),
    linear-gradient(118deg, rgb(255 255 255 / 18%), transparent 58%, rgb(255 255 255 / 12%)) !important;
  color: var(--alx-text) !important; font-weight: 620 !important;
  box-shadow: inset 0 1px 0 var(--alx-glass-highlight),
    inset 0 -1px 0 rgb(79 70 229 / 8%), var(--alx-glass-shadow) !important;
  backdrop-filter: blur(var(--alx-glass-blur)) saturate(148%) contrast(102%);
  -webkit-backdrop-filter: blur(var(--alx-glass-blur)) saturate(148%) contrast(102%);
  transform: translateY(0);
  transition: transform 420ms var(--alx-ease-fluid), border-color 420ms var(--alx-ease-fluid),
    box-shadow 420ms var(--alx-ease-fluid), background-color 420ms var(--alx-ease-fluid);
}
.gradio-container button.primary::before {
  content: ""; position: absolute; z-index: -1; inset: 1px; pointer-events: none;
  border-radius: inherit;
  background: linear-gradient(105deg, transparent 22%, rgb(255 255 255 / 58%) 49%, transparent 70%);
  transform: translateX(-120%); transition: transform 720ms var(--alx-ease-fluid);
}
.gradio-container button.primary:hover {
  border-color: rgb(255 255 255 / 84%) !important;
  background-color: var(--alx-glass-fill-hover) !important;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 80%),
    inset 0 -1px 0 rgb(79 70 229 / 7%), 0 24px 62px rgb(71 105 148 / 16%),
    0 0 32px rgb(255 255 255 / 16%) !important;
  transform: translateY(-3px);
}
.gradio-container button.primary:hover::before { transform: translateX(118%); }
.gradio-container button.primary:active { transform: translateY(-1px) scale(.985); }
.gradio-container button.primary:focus-visible {
  outline: none !important;
  box-shadow: 0 0 0 3px rgb(239 248 255), 0 0 0 6px rgb(37 99 235 / 60%),
    var(--alx-glass-shadow) !important;
}
.gradio-container button.secondary {
  min-height: 44px; border: 1px solid var(--alx-glass-edge) !important;
  border-radius: var(--alx-radius-pill) !important;
  background: rgb(255 255 255 / 44%) !important; color: var(--alx-reading) !important;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 62%), 0 12px 32px rgb(71 105 148 / 8%) !important;
  backdrop-filter: blur(18px) saturate(132%);
  -webkit-backdrop-filter: blur(18px) saturate(132%);
  transition: transform 360ms var(--alx-ease-fluid), border-color 360ms var(--alx-ease-fluid),
    background-color 360ms var(--alx-ease-fluid);
}
.gradio-container button.secondary:hover {
  border-color: rgb(255 255 255 / 84%) !important;
  background: rgb(255 255 255 / 62%) !important; transform: translateY(-1px);
}
.gradio-container button.secondary:active { transform: scale(.985); }
.gradio-container button.secondary:focus-visible {
  outline: 3px solid rgb(37 99 235 / 42%) !important; outline-offset: 2px;
}
.gradio-container textarea, .gradio-container input { font-size: 13px !important; }
#studio-report-table { font-family: var(--alx-font-sans); font-feature-settings: "ss02" 1, "tnum" 1;
  font-variant-numeric: tabular-nums; font-size: 11px; }
@media (max-width: 940px) {
  #alvenx-header { grid-template-columns: 1fr auto; }
  .header-tagline { display: none; }
  .proof-grid { grid-template-columns: repeat(2,1fr); }
  .model-lane { grid-template-columns: 1fr 1fr; }
  .status-cell { justify-self: start; }
  .workflow-grid { grid-template-columns: 1fr; }
  .studio-workspace { flex-direction: column !important; }
  .workspace-panel { width: 100% !important; height: auto; overflow-y: visible; }
  .workspace-output #studio-response textarea { min-height: 300px !important; }
}
@media (min-width: 941px) and (max-height: 850px) {
  #alvenx-header { margin-top: 0; padding-block: 2px; }
  .brand-wordmark-image { width: 150px; }
  .tab-intro { padding-top: 6px; padding-bottom: 6px; }
  .workspace-panel { padding: 14px !important; }
  .workspace-panel-header { min-height: 46px; margin-bottom: 10px; padding-bottom: 10px; }
  .studio-media-input { height: auto !important; min-height: 180px;
    max-height: none !important; overflow: visible !important; }
  .workspace-output #studio-response textarea { min-height: 220px !important; }
  .metric-panel { min-height: 165px; padding: 16px; }
}
@media (max-width: 620px) {
  .gradio-container { padding-inline: 10px !important; }
  #studio-tabs { margin-top: -6px !important; }
  #alvenx-header { margin-top: 2px; padding-inline: 2px; }
  .brand-wordmark-image { width: 150px; }
  .local-badge { gap: 5px; padding: 6px 8px; font-size: 10px; }
  .hero-panel { min-height: 300px; padding: 38px 25px; }
  .hero-panel h1 { font-size: 40px; }
  .proof-grid, .live-grid { grid-template-columns: 1fr; }
  .model-lane { grid-template-columns: 1fr; gap: 10px; }
  .tab-intro, .section-heading { align-items: flex-start; flex-direction: column; }
  .workspace-panel { padding: 13px !important; border-radius: 17px; }
  .workspace-panel-header { min-height: 0; }
  .panel-note { display: none; }
  .studio-media-input { min-height: 220px; }
  .studio-media-input img, .studio-media-input video { max-height: 360px !important; }
}
@media (prefers-reduced-motion: reduce) {
  .gradio-container *, .gradio-container *::before, .gradio-container *::after {
    transition-duration: .01ms !important;
  }
}
""").strip()


EASTER_EGG_JS = """
(() => {
  let wordmarkClicks = 0;
  let resetTimer = null;
  const signal = () => document.getElementById("alonica-signal");
  const openSignal = () => {
    const panel = signal();
    if (!panel) return;
    panel.hidden = false;
    document.getElementById("alonica-close")?.focus();
  };
  const closeSignal = () => {
    const panel = signal();
    if (panel) panel.hidden = true;
    document.getElementById("alvenx-wordmark-button")?.focus();
  };
  const bind = () => {
    const wordmark = document.getElementById("alvenx-wordmark-button");
    const close = document.getElementById("alonica-close");
    if (wordmark && !wordmark.dataset.alonicaBound) {
      wordmark.dataset.alonicaBound = "true";
      wordmark.addEventListener("click", () => {
        wordmarkClicks += 1;
        clearTimeout(resetTimer);
        resetTimer = setTimeout(() => { wordmarkClicks = 0; }, 2500);
        if (wordmarkClicks >= 5) { wordmarkClicks = 0; openSignal(); }
      });
    }
    if (close && !close.dataset.alonicaBound) {
      close.dataset.alonicaBound = "true";
      close.addEventListener("click", closeSignal);
    }
  };
  bind();
  new MutationObserver(bind).observe(document.body, { childList: true, subtree: true });
  document.addEventListener("keydown", (event) => {
    if (event.altKey && event.key.toLowerCase() === "a") {
      event.preventDefault(); openSignal();
    } else if (event.key === "Escape" && signal() && !signal().hidden) {
      closeSignal();
    }
  });
})();
""".strip()

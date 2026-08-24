"""Content, renderers, and packaged presentation assets for OpenMultimodalLab."""

from __future__ import annotations

import base64
import hashlib
from html import escape
from importlib.resources import files
from pathlib import Path

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
    "8ae10e02c27091e29e0191a7934506118f144aae11898b20222d7f9d587e2662"
)
ALVENX_MONOGRAM_SHA256 = (
    "45367ec933c2ed8565cdf9e683fd4b856057d375435b46c62acb4fbb2cbeef16"
)


def _verified_monogram_path() -> Path:
    path = Path(__file__).resolve().parent / "assets/brand/alvenx-monogram.svg"
    payload = path.read_bytes()
    if (
        not payload.lstrip().startswith(b"<svg")
        or hashlib.sha256(payload).hexdigest() != ALVENX_MONOGRAM_SHA256
    ):
        raise RuntimeError("The bundled AX monogram failed integrity check.")
    return path


ALVENX_MONOGRAM_PATH = _verified_monogram_path()


def _verified_base64(relative: str, expected_sha256: str, magic: bytes) -> str:
    payload = files("openmultimodal_lab").joinpath(relative).read_text(encoding="ascii")
    encoded = "".join(payload.split())
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"The bundled asset {relative} is corrupt.") from exc
    if (
        not decoded.lstrip().startswith(magic)
        or hashlib.sha256(decoded).hexdigest() != expected_sha256
    ):
        raise RuntimeError(f"The bundled asset {relative} failed integrity check.")
    return encoded


def _instrument_sans_base64() -> str:
    return _verified_base64(
        "assets/fonts/InstrumentSans-wdth-wght.woff2.b64",
        INSTRUMENT_SANS_SHA256,
        b"wOF2",
    )


def _alvenx_wordmark_base64() -> str:
    return _verified_base64(
        "assets/brand/alvenx-wordmark.svg.b64",
        ALVENX_WORDMARK_SHA256,
        b"<svg",
    )


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


def _studio_theme() -> str:
    return files("openmultimodal_lab").joinpath(
        "assets/studio/alvenx-studio.css"
    ).read_text(encoding="utf-8")


BRAND_HEADER_HTML = f"""
<header id="alvenx-header" class="studio-shell">
  <div class="brand-wordmark">
    <img class="brand-wordmark-image"
         src="data:image/svg+xml;base64,{_alvenx_wordmark_base64()}"
         alt="AlvenX">
  </div>
  <nav class="header-nav" aria-label="OpenMultimodalLab views">
    <button type="button" class="active" data-studio-tab="run" aria-current="page">Run</button>
    <button type="button" data-studio-tab="reports">Reports</button>
    <button type="button" data-studio-tab="method">Method</button>
  </nav>
  <span class="local-badge"><i aria-hidden="true"></i> Local only</span>
</header>
""".strip()


STUDIO_NAV_JS = r"""(() => {
  document.title = "OpenMultimodalLab · AlvenX";
  let attempts = 0;
  const bind = () => {
    const header = document.querySelector("#alvenx-header");
    const tabRoot = document.querySelector("#studio-tabs > .tab-wrapper");
    if (!header || !tabRoot) {
      if (attempts++ < 240) requestAnimationFrame(bind);
      return;
    }

    const controls = [...header.querySelectorAll("[data-studio-tab]")];
    const tabs = () => [...tabRoot.querySelectorAll("button[role='tab']")];
    tabRoot.setAttribute("aria-hidden", "true");
    tabs().forEach((tab) => { tab.tabIndex = -1; });
    const sync = () => {
      const selected = tabs().find((tab) => tab.getAttribute("aria-selected") === "true");
      controls.forEach((control) => {
        const active = control.dataset.studioTab === selected?.dataset.tabId;
        control.classList.toggle("active", active);
        active
          ? control.setAttribute("aria-current", "page")
          : control.removeAttribute("aria-current");
      });
    };

    controls.forEach((control) => {
      control.onclick = () => {
        tabs().find((tab) => tab.dataset.tabId === control.dataset.studioTab)?.click();
        sync();
      };
    });
    new MutationObserver(sync).observe(tabRoot, {
      attributes: true,
      subtree: true,
      attributeFilter: ["aria-selected"],
    });
    sync();
  };
  bind();
})();"""


WORKSPACE_GUIDE_HTML = """
<section class="run-map" aria-labelledby="run-map-title">
  <header>
    <span class="kicker">LOCAL MULTIMODAL WORKBENCH</span>
    <h1 id="run-map-title">Turn one source into inspectable evidence.</h1>
    <p>Select media, set the model contract, run locally, then read the response
       beside the measurements that produced it.</p>
  </header>
  <ol>
    <li><span>01</span><strong>Source</strong><small>image, document, or video</small></li>
    <li><span>02</span><strong>Model</strong><small>one pinned local backend</small></li>
    <li><span>03</span><strong>Prompt</strong><small>bounded generation controls</small></li>
    <li><span>04</span><strong>Evidence</strong><small>output and runtime signals</small></li>
  </ol>
  <aside><span aria-hidden="true">●</span><strong>Nothing leaves this machine.</strong>
    <small>Runs stay unscored until evaluated by a versioned task protocol.</small></aside>
</section>
""".strip()


WORKSPACE_INPUT_HEADER_HTML = """
<header class="workspace-panel-header">
  <div><span class="panel-index">01</span><span class="kicker">RUN CONFIGURATION</span>
    <h2>Prepare the experiment</h2></div>
  <span class="panel-note">Cold load once · warm reuse</span>
</header>
""".strip()


WORKSPACE_OUTPUT_HEADER_HTML = """
<header class="workspace-panel-header">
  <div><span class="panel-index">02</span><span class="kicker">EVIDENCE CONSOLE</span>
    <h2>Read result and runtime together</h2></div>
  <span class="panel-note">Preview · not a benchmark score</span>
</header>
""".strip()


IMAGE_UPLOAD_GUIDANCE_HTML = """
<div class="media-guidance" role="note">
  <strong>Image or document</strong>
  <span>Up to 25 MiB · full frame preserved · paste or upload.</span>
</div>
""".strip()


VIDEO_UPLOAD_GUIDANCE_HTML = """
<div class="media-guidance" role="note">
  <strong>Short video</strong>
  <span>Up to 50 MiB · 60 seconds · 3,600 frames · 4K. H.264 MP4 provides the
        most portable moving preview.</span>
</div>
""".strip()


REPORT_INTRO_HTML = """
<section class="report-intro">
  <div><span class="kicker">DURABLE EVIDENCE</span>
    <h1>Inspect a run without rewriting it.</h1></div>
  <p>Open a JSONL record produced by <code>oml run</code>. Summary, protocol status,
     and individual attempts remain traceable to the source file.</p>
</section>
""".strip()


OVERVIEW_HTML = """
<main class="method-stack studio-shell">
  <section class="method-hero">
    <span class="kicker">OPENMULTIMODALLAB · V1</span>
    <h1>Measurement software,<br><em>not a model leaderboard.</em></h1>
    <p>OpenMultimodalLab runs pinned local vision-language models against versioned
       tasks and preserves enough evidence to reproduce, inspect, and challenge a result.</p>
  </section>
  <section class="method-facts" aria-label="Version 1 scope">
    <article><span>Task set</span><strong>102</strong><small>human-checked tasks</small></article>
    <article><span>Backends</span><strong>2</strong><small>real open models</small></article>
    <article><span>Evidence</span><strong>612</strong><small>measured attempts</small></article>
    <article><span>Target</span><strong>8 GB</strong><small>consumer GPU profile</small></article>
  </section>
  <section class="method-grid">
    <article><span>01 · CONTROL</span><h2>Pin what changes.</h2>
      <p>Task, media, prompt, backend revision, warm-up, repetitions, and hardware
         context belong in the record—not in memory.</p></article>
    <article><span>02 · MEASURE</span><h2>Separate quality from speed.</h2>
      <p>Scores, latency, TTFT, throughput, and peak memory answer different questions.
         The interface never collapses them into one magic number.</p></article>
    <article><span>03 · INTERPRET</span><h2>Keep the boundary visible.</h2>
      <p>A playground response is unscored. A formal comparison requires the versioned
         task protocol and its preserved JSONL evidence.</p></article>
  </section>
</main>
""".strip()


EMPTY_METRICS_HTML = """
<section class="metric-panel empty-state">
  <div class="panel-top"><span class="kicker">LIVE TELEMETRY</span>
    <span class="unscored-pill">UNSCORED</span></div>
  <h3>Run evidence will appear here.</h3>
  <p>Wall latency, TTFT, output throughput, peak GPU memory, backend revision, and
     output length are reported when the adapter provides them.</p>
</section>
""".strip()


EMPTY_STATUS_HTML = """
<div class="run-status idle"><span aria-hidden="true"></span><strong>Ready for a cold run.</strong>
The selected model loads once, then remains warm for later runs.</div>
""".strip()


CLEARED_STATUS_HTML = """
<div class="run-status idle"><span aria-hidden="true"></span><strong>Run cleared.</strong>
Inputs and output were reset; any loaded model remains warm.</div>
""".strip()


EMPTY_REPORT_HTML = """
<section class="metric-panel empty-state">
  <div class="panel-top"><span class="kicker">RUN SUMMARY</span>
    <span class="protocol-pill informal">NO FILE</span></div>
  <h3>Select one preserved JSONL record.</h3>
  <p>The report view is read-only and never modifies the evidence file.</p>
</section>
""".strip()


def render_video_upload_info(info: VideoUploadInfo) -> str:
    """Explain browser playback separately from model decoding."""

    codec = info.codec.casefold()
    if codec in {"hevc", "h265"}:
        status_class = "warning"
        title = "HEVC/H.265 · model-readable"
        message = (
            "Browser playback may play only the audio or hold one frame. "
            "Local model analysis still uses PyAV; "
            "use H.264 MP4 when a moving preview matters."
        )
    elif codec in {"h264", "avc", "avc1"}:
        status_class = "compatible"
        title = "H.264 · portable preview"
        message = "The original upload remains the local model input."
    else:
        status_class = "neutral"
        title = f"{info.codec.upper() or 'UNKNOWN'} · playback varies"
        message = "Browser playback and local model decoding are separate capabilities."

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
        f"<strong>{escape(title)}</strong><span>{escape(message)}</span>"
        '<small class="media-facts">'
        f"{info.width}×{info.height} · {escape(duration)} · {escape(frames)} · "
        f"{escape(fps)} · {size_mib:.2f} MiB</small></div>"
    )


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
        f"<span>{escape(label)}</span><strong>{escape(value)}</strong>{note_html}</article>"
    )


def render_playground_metrics(result: PlaygroundResult) -> str:
    usage = result.usage
    cards = [
        _metric_card("Wall latency", _metric_value(result.latency_ms, " ms")),
        _metric_card("TTFT", _metric_value(usage.get("ttft_ms"), " ms")),
        _metric_card(
            "Output rate",
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
    return (
        '<section class="metric-panel"><div class="panel-top">'
        '<span class="kicker">LIVE TELEMETRY</span>'
        '<span class="unscored-pill">UNSCORED</span></div>'
        f'<div class="live-grid">{"".join(cards)}</div>'
        '<div class="runtime-foot">'
        f"<span>Backend <strong>{escape(result.backend)}</strong></span>"
        f"<span>Revision <code>{escape(result.model_revision[:12])}</code></span>"
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
            else "Ask for a shorter answer or split the prompt."
        )
        return (
            '<div class="run-status warning"><span aria-hidden="true"></span>'
            f"<strong>Completed at the {token_limit}-token limit.</strong> "
            f"The final sentence may be truncated. {next_step}</div>"
        )
    return (
        '<div class="run-status success"><span aria-hidden="true"></span>'
        f"<strong>Completed locally.</strong> Model warm · {escape(result.media_kind)} · "
        "no quality score assigned</div>"
    )


def render_error_status(message: str) -> str:
    return (
        '<div class="run-status error"><span aria-hidden="true"></span>'
        f"<strong>Run stopped.</strong> {escape(message)}</div>"
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
        '<section class="metric-panel"><div class="panel-top"><div>'
        f'<span class="kicker">RUN SUMMARY</span><h3>{escape(view.filename)}</h3></div>'
        f'<span class="protocol-pill {protocol_class}">{protocol_label}</span></div>'
        f'<div class="live-grid">{"".join(cards)}</div>'
        '<div class="runtime-foot">'
        f"<span>Records <strong>{int(summary.get('total_records', 0))}</strong></span>"
        f"<span>Unique tasks <strong>{int(summary.get('unique_tasks', 0))}</strong></span>"
        f"<span>Repetitions <strong>{int(summary.get('repetitions', 0))}</strong></span>"
        f"<span>Failures <strong>{escape(str(summary.get('failures', {})))}</strong></span>"
        "</div></section>"
    )


STUDIO_CSS = _INSTRUMENT_SANS_FONT_FACE + _studio_theme()

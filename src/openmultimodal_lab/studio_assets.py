"""Brand copy, accessible HTML, CSS, and interactions for Ailumetra Studio."""

from __future__ import annotations

from html import escape
from typing import Any

from .studio import PlaygroundResult, ReportView


BRAND_HEADER_HTML = """
<header id="ailumetra-header" class="studio-shell">
  <button id="ailumetra-wordmark-button" class="brand-wordmark" type="button"
          aria-label="Ailumetra wordmark" title="Ailumetra">
    <span class="brand-name">Ailumetra</span>
    <span class="brand-product">STUDIO</span>
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
  <code>Ailumetra Studio · signal 01</code>
</section>
""".strip()


OVERVIEW_HTML = """
<main class="overview-stack studio-shell">
  <section class="hero-panel">
    <div class="eyebrow">LOCAL-FIRST MULTIMODAL EVALUATION</div>
    <h1>From media to evidence,<br><span>on hardware you own.</span></h1>
    <p>Ailumetra is the product layer for OpenMultimodalLab: run real vision-language
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


PLAYGROUND_INTRO_HTML = """
<section class="tab-intro">
  <div><span class="eyebrow">PLAYGROUND</span><h2>Ask one local model</h2></div>
  <p>This is an unscored interactive inference, not a formal benchmark result.</p>
</section>
""".strip()


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
<div class="run-status idle"><span></span>Ready · no model is loaded yet</div>
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
        "</div></section>"
    )


def render_success_status(result: PlaygroundResult) -> str:
    return (
        '<div class="run-status success"><span></span>'
        f"Completed locally · {escape(result.media_kind)} · no quality score assigned"
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


STUDIO_CSS = """
:root {
  --ail-bg: #070b12;
  --ail-panel: #0d1420;
  --ail-panel-2: #111b2a;
  --ail-border: rgba(148, 163, 184, 0.16);
  --ail-text: #e7edf6;
  --ail-muted: #8ea0b8;
  --ail-teal: #2dd4bf;
  --ail-blue: #60a5fa;
  --ail-violet: #a78bfa;
  --ail-red: #fb7185;
  --ail-amber: #fbbf24;
}
body, .gradio-container {
  background:
    radial-gradient(circle at 78% -10%, rgba(96,165,250,.12), transparent 34rem),
    radial-gradient(circle at 20% 20%, rgba(45,212,191,.08), transparent 30rem),
    var(--ail-bg) !important;
  color: var(--ail-text) !important;
}
.gradio-container {
  max-width: 1480px !important; margin: 0 auto !important;
  --body-background-fill: var(--ail-bg);
  --body-text-color: var(--ail-text);
  --body-text-color-subdued: var(--ail-muted);
  --background-fill-primary: var(--ail-panel);
  --background-fill-secondary: var(--ail-panel-2);
  --block-background-fill: var(--ail-panel);
  --block-label-background-fill: var(--ail-panel);
  --block-label-text-color: #b9c7d8;
  --block-title-text-color: var(--ail-text);
  --input-background-fill: #111b2a;
  --input-border-color: rgba(148,163,184,.22);
  --input-placeholder-color: #64748b;
  --border-color-primary: rgba(148,163,184,.18);
  --border-color-accent: var(--ail-blue);
  --button-secondary-background-fill: #172235;
  --button-secondary-background-fill-hover: #1d2b42;
  --button-secondary-text-color: #d8e3f0;
  --button-secondary-text-color-hover: #ffffff;
  --table-odd-background-fill: rgba(17,27,42,.7);
  --table-even-background-fill: rgba(13,20,32,.7);
}
.gradio-container .prose, .brand-name, .hero-panel h1,
.section-heading h2, .tab-intro h2, .comparison-panel strong,
.workflow-grid h3, .metric-panel h3 { color: var(--ail-text) !important; }
.gradio-container button[role="tab"] {
  color: #91a4bc !important; background: transparent !important;
}
.gradio-container button[role="tab"][aria-selected="true"] {
  color: var(--ail-blue) !important;
}
.studio-shell { margin-left: auto; margin-right: auto; }
#ailumetra-header {
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
  margin: 18px 4px 10px; padding: 12px 16px;
  border: 1px solid var(--ail-border); border-radius: 16px;
  background: rgba(13,20,32,.82); backdrop-filter: blur(16px);
  box-shadow: 0 18px 70px rgba(0,0,0,.24);
}
.brand-wordmark { display: inline-flex; flex-direction: column; align-items: flex-start;
  width: max-content; padding: 4px 6px; border: 0; border-radius: 8px;
  background: transparent; color: inherit; cursor: pointer;
  font-family: Arial, Helvetica, ui-sans-serif, sans-serif; }
.brand-wordmark:focus-visible { outline: 2px solid var(--ail-teal); outline-offset: 3px; }
.brand-name { font-size: 22px; line-height: 1; font-weight: 700; letter-spacing: -.035em; }
.brand-product { color: var(--ail-muted); font-size: 9px; font-weight: 600;
  letter-spacing: .28em; margin-top: 6px; }
.header-tagline { color: #b9c7d8; font-size: 13px; letter-spacing: .02em; }
.local-badge { justify-self: end; display: inline-flex; align-items: center; gap: 7px;
  color: #b9f7ec; font-size: 12px; font-weight: 650; padding: 7px 10px;
  border: 1px solid rgba(45,212,191,.22); background: rgba(45,212,191,.08);
  border-radius: 999px; }
.local-badge span, .run-status > span { width: 7px; height: 7px; border-radius: 50%;
  background: var(--ail-teal); box-shadow: 0 0 13px rgba(45,212,191,.8); }
.developer-signal { position: fixed; z-index: 99999; top: 50%; left: 50%;
  transform: translate(-50%,-50%); width: min(440px, calc(100vw - 36px));
  padding: 30px; border: 1px solid rgba(45,212,191,.42); border-radius: 18px;
  background: #071019; color: var(--ail-text); box-shadow: 0 30px 100px #000;
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace; }
.developer-signal[hidden] { display: none; }
.developer-signal:before { content: ""; position: absolute; inset: 0; pointer-events: none;
  border-radius: inherit; background: repeating-linear-gradient(0deg,transparent 0 4px,
  rgba(45,212,191,.025) 5px); }
.developer-signal button { position: absolute; top: 10px; right: 12px; width: 32px;
  border: 0; background: transparent; color: var(--ail-muted); font-size: 24px; cursor: pointer; }
.signal-kicker, .eyebrow { color: var(--ail-teal); font-size: 10px; font-weight: 750;
  letter-spacing: .18em; }
.developer-signal h2 { margin: 13px 0 4px; font-size: 21px; }
.developer-signal p { color: #9fb2c7; margin: 0 0 18px; }
.developer-signal code { color: var(--ail-violet); }
.overview-stack { display: grid; gap: 14px; padding: 4px; }
.hero-panel, .comparison-panel, .metric-panel, .workflow-grid article, .proof-grid article {
  border: 1px solid var(--ail-border); background: linear-gradient(145deg,
  rgba(17,27,42,.92),rgba(10,16,26,.96)); box-shadow: 0 18px 60px rgba(0,0,0,.16); }
.hero-panel { position: relative; overflow: hidden; min-height: 330px; padding: 58px 52px;
  border-radius: 22px; display: flex; flex-direction: column; justify-content: center; }
.hero-panel:after { content: "A"; position: absolute; right: 4%; top: -25%; font-size: 400px;
  font-weight: 800; color: transparent; -webkit-text-stroke: 1px rgba(96,165,250,.09);
  transform: rotate(5deg); pointer-events: none; }
.hero-panel h1 { margin: 15px 0 16px; max-width: 830px; font-size: clamp(38px,6vw,72px);
  line-height: .98; letter-spacing: -.055em; font-weight: 730; }
.hero-panel h1 span {
  background-image: linear-gradient(90deg,var(--ail-teal),var(--ail-blue),var(--ail-violet)) !important;
  -webkit-background-clip: text !important; background-clip: text !important;
  color: transparent !important;
}
.hero-panel > p { max-width: 720px; color: #9fb0c6; line-height: 1.65; font-size: 15px; }
.hero-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.hero-pills span, .evidence-pill { border: 1px solid var(--ail-border); color: #c2cede;
  background: rgba(148,163,184,.06); border-radius: 999px; padding: 7px 10px; font-size: 11px; }
.proof-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; }
.proof-grid article { padding: 23px; border-radius: 16px; }
.proof-grid strong { display: block; font-size: 30px; letter-spacing: -.04em; }
.proof-grid span { color: var(--ail-muted); font-size: 12px; }
.comparison-panel { padding: 28px; border-radius: 20px; }
.section-heading, .panel-top { display: flex; justify-content: space-between; align-items: center;
  gap: 18px; margin-bottom: 20px; }
.section-heading h2, .tab-intro h2 { margin: 7px 0 0; font-size: 25px; letter-spacing: -.035em; }
.model-lane { display: grid; grid-template-columns: minmax(210px,1.5fr) minmax(160px,1fr)
  minmax(120px,.8fr) minmax(135px,.9fr) 92px; gap: 20px; align-items: center;
  padding: 20px 4px; border-top: 1px solid var(--ail-border); }
.model-title { display: flex; align-items: center; gap: 12px; }
.model-title strong { display: block; font-size: 15px; }
.model-title small, .score-cell span, .number-cell span { display: block; color: var(--ail-muted);
  font-size: 10px; margin-bottom: 4px; }
.model-dot { width: 10px; height: 10px; border-radius: 50%; }
.model-dot.qwen { background: var(--ail-violet); box-shadow: 0 0 16px rgba(167,139,250,.65); }
.model-dot.smol { background: var(--ail-blue); box-shadow: 0 0 16px rgba(96,165,250,.65); }
.score-cell strong, .number-cell strong { font-family: ui-monospace,"Cascadia Code",Consolas,monospace;
  font-size: 15px; }
.score-track { height: 3px; margin-top: 7px; background: #1e293b; border-radius: 10px; overflow: hidden; }
.score-track i { display: block; height: 100%; background: linear-gradient(90deg,var(--ail-teal),var(--ail-blue)); }
.status-cell { justify-self: end; font-family: ui-monospace,"Cascadia Code",Consolas,monospace;
  font-size: 10px; padding: 6px 8px; border-radius: 7px; }
.status-cell.success { color: #9df4e5; background: rgba(45,212,191,.08); }
.evidence-note { margin: 15px 0 0; color: #70839b; font-size: 11px; line-height: 1.6; }
.workflow-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; background: transparent;
  border: 0; box-shadow: none; }
.workflow-grid article { border-radius: 16px; padding: 25px; }
.workflow-grid article > span { color: var(--ail-teal); font-family: ui-monospace,monospace; font-size: 11px; }
.workflow-grid h3 { margin: 16px 0 8px; font-size: 16px; }
.workflow-grid p { margin: 0; color: var(--ail-muted); font-size: 12px; line-height: 1.6; }
.tab-intro { display: flex; align-items: end; justify-content: space-between; gap: 20px;
  padding: 18px 6px 10px; }
.tab-intro p { color: var(--ail-muted); font-size: 12px; }
.metric-panel { padding: 24px; border-radius: 18px; min-height: 250px; }
.metric-panel h3 { margin: 8px 0 0; font-size: 17px; }
.empty-state { display: flex; flex-direction: column; justify-content: center; }
.empty-state p { color: var(--ail-muted); max-width: 450px; line-height: 1.6; font-size: 12px; }
.live-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 10px; }
.live-card { padding: 16px; border: 1px solid var(--ail-border); border-radius: 12px;
  background: rgba(3,8,15,.28); }
.live-card span { display: block; color: var(--ail-muted); font-size: 10px; margin-bottom: 7px; }
.live-card strong { font-family: ui-monospace,"Cascadia Code",Consolas,monospace;
  font-size: 17px; letter-spacing: -.025em; }
.live-card small { display: block; margin-top: 6px; color: #64748b; font-size: 9px; }
.unscored-pill, .protocol-pill { padding: 6px 8px; border-radius: 7px; font-size: 9px;
  font-weight: 750; letter-spacing: .12em; }
.unscored-pill, .protocol-pill.informal { color: #fcd77f; background: rgba(251,191,36,.09); }
.protocol-pill.formal { color: #8df1df; background: rgba(45,212,191,.09); }
.runtime-foot { display: flex; flex-wrap: wrap; gap: 14px 20px; border-top: 1px solid var(--ail-border);
  margin-top: 18px; padding-top: 14px; color: var(--ail-muted); font-size: 10px; }
.runtime-foot strong, .runtime-foot code { color: #c8d4e3; }
.run-status { display: flex; align-items: center; gap: 8px; padding: 10px 13px;
  border: 1px solid var(--ail-border); border-radius: 11px; color: var(--ail-muted); font-size: 11px; }
.run-status.idle > span { background: #64748b; box-shadow: none; }
.run-status.error { color: #fecdd3; border-color: rgba(251,113,133,.25); }
.run-status.error > span { background: var(--ail-red); box-shadow: 0 0 12px rgba(251,113,133,.6); }
.gradio-container .form, .gradio-container .block { border-color: var(--ail-border) !important; }
.gradio-container button.primary { background: linear-gradient(100deg,#159f91,#347fc9) !important;
  border: 0 !important; box-shadow: 0 9px 25px rgba(45,212,191,.14) !important; }
.gradio-container textarea, .gradio-container input { font-size: 13px !important; }
#studio-report-table { font-family: ui-monospace,"Cascadia Code",Consolas,monospace; font-size: 11px; }
@media (max-width: 940px) {
  #ailumetra-header { grid-template-columns: 1fr auto; }
  .header-tagline { display: none; }
  .proof-grid { grid-template-columns: repeat(2,1fr); }
  .model-lane { grid-template-columns: 1fr 1fr; }
  .status-cell { justify-self: start; }
  .workflow-grid { grid-template-columns: 1fr; }
}
@media (max-width: 620px) {
  #ailumetra-header { margin-top: 8px; }
  .local-badge { font-size: 0; }
  .local-badge span { margin: 3px; }
  .hero-panel { min-height: 300px; padding: 38px 25px; }
  .hero-panel h1 { font-size: 40px; }
  .proof-grid, .live-grid { grid-template-columns: 1fr; }
  .model-lane { grid-template-columns: 1fr; gap: 10px; }
  .tab-intro, .section-heading { align-items: flex-start; flex-direction: column; }
}
""".strip()


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
    document.getElementById("ailumetra-wordmark-button")?.focus();
  };
  const bind = () => {
    const wordmark = document.getElementById("ailumetra-wordmark-button");
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

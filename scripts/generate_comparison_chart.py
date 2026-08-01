"""Generate the README comparison chart from preserved formal JSONL results."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openmultimodal_lab.reporting import load_records, summarize


@dataclass(frozen=True, slots=True)
class ModelResult:
    label: str
    color: str
    mean_score: float
    median_latency_ms: float
    median_ttft_ms: float
    peak_gpu_memory_mb: float
    successful_tasks: int
    total_tasks: int


def _number(summary: dict[str, Any], key: str) -> float:
    value = summary.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"comparison result has no numeric {key}")
    return float(value)


def _load_result(path: Path, *, label: str, color: str) -> ModelResult:
    summary = summarize(load_records(path))
    if not summary["formal_performance_run"]:
        raise ValueError(f"comparison result is not a formal run: {path}")
    return ModelResult(
        label=label,
        color=color,
        mean_score=_number(summary, "mean_score"),
        median_latency_ms=_number(summary, "median_latency_ms"),
        median_ttft_ms=_number(summary, "median_ttft_ms"),
        peak_gpu_memory_mb=_number(summary, "peak_gpu_memory_mb"),
        successful_tasks=int(summary["successful_tasks"]),
        total_tasks=int(summary["total_tasks"]),
    )


def _bar(
    *,
    y: int,
    value: float,
    maximum: float,
    color: str,
    text: str,
) -> str:
    x = 255
    width = 835
    filled = max(0.0, min(value / maximum, 1.0)) * width
    end = x + filled
    if end > 1010:
        label_x = end - 12
        anchor = "end"
        label_color = "#07111f"
    else:
        label_x = end + 12
        anchor = "start"
        label_color = "#f4f8fc"
    return f"""    <rect x="{x}" y="{y}" width="{width}" height="20" rx="10" fill="#172a40"/>
    <rect x="{x}" y="{y}" width="{filled:.1f}" height="20" rx="10" fill="{color}"/>
    <text x="{label_x:.1f}" y="{y + 15}" text-anchor="{anchor}" class="value" fill="{label_color}">{text}</text>"""


def render_chart(qwen: ModelResult, smol: ModelResult) -> str:
    if qwen.total_tasks != smol.total_tasks:
        raise ValueError("comparison runs do not contain the same attempt count")
    if qwen.successful_tasks != qwen.total_tasks:
        raise ValueError("Qwen comparison contains failed measurements")
    if smol.successful_tasks != smol.total_tasks:
        raise ValueError("SmolVLM2 comparison contains failed measurements")

    score_gap = qwen.mean_score - smol.mean_score
    latency_reduction = (
        (smol.median_latency_ms - qwen.median_latency_ms)
        / smol.median_latency_ms
        * 100
    )
    memory_reduction = (
        (qwen.peak_gpu_memory_mb - smol.peak_gpu_memory_mb)
        / qwen.peak_gpu_memory_mb
        * 100
    )

    qwen_score = _bar(
        y=239,
        value=qwen.mean_score,
        maximum=1.0,
        color=qwen.color,
        text=f"{qwen.mean_score:.3f}",
    )
    smol_score = _bar(
        y=268,
        value=smol.mean_score,
        maximum=1.0,
        color=smol.color,
        text=f"{smol.mean_score:.3f}",
    )
    qwen_latency = _bar(
        y=359,
        value=qwen.median_latency_ms,
        maximum=450.0,
        color=qwen.color,
        text=f"{qwen.median_latency_ms:.0f} ms",
    )
    smol_latency = _bar(
        y=388,
        value=smol.median_latency_ms,
        maximum=450.0,
        color=smol.color,
        text=f"{smol.median_latency_ms:.0f} ms",
    )
    qwen_memory = _bar(
        y=479,
        value=qwen.peak_gpu_memory_mb,
        maximum=4500.0,
        color=qwen.color,
        text=f"{qwen.peak_gpu_memory_mb:,.0f} MiB",
    )
    smol_memory = _bar(
        y=508,
        value=smol.peak_gpu_memory_mb,
        maximum=4500.0,
        color=smol.color,
        text=f"{smol.peak_gpu_memory_mb:,.0f} MiB",
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title description">
  <title id="title">Formal Qwen3-VL-2B and SmolVLM2-500M comparison</title>
  <desc id="description">Qwen has higher mean task score and lower median latency. SmolVLM2 uses substantially less peak GPU memory on the same ten-task local benchmark.</desc>
  <defs>
    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#07111f"/>
      <stop offset="1" stop-color="#0c1d32"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.82" cy="0.05" r="0.8">
      <stop offset="0" stop-color="#244d72" stop-opacity="0.42"/>
      <stop offset="1" stop-color="#07111f" stop-opacity="0"/>
    </radialGradient>
    <style>
      text {{ font-family: Inter, "Segoe UI", Arial, sans-serif; }}
      .eyebrow {{ font-size: 15px; font-weight: 600; letter-spacing: 2.2px; fill: #7f96ad; }}
      .title {{ font-size: 42px; font-weight: 700; fill: #f4f8fc; }}
      .subtitle {{ font-size: 18px; font-weight: 400; fill: #9fb2c7; }}
      .metric {{ font-size: 16px; font-weight: 700; letter-spacing: 1.2px; fill: #dce8f3; }}
      .scale {{ font-size: 13px; font-weight: 400; fill: #7890a8; }}
      .model {{ font-size: 16px; font-weight: 600; fill: #dce8f3; }}
      .value {{ font-size: 14px; font-weight: 700; }}
      .takeaway {{ font-size: 17px; font-weight: 600; fill: #f4f8fc; }}
      .protocol {{ font-size: 14px; font-weight: 400; fill: #8fa4b9; }}
      .limit {{ font-size: 13px; font-weight: 600; fill: #6f879f; letter-spacing: 0.4px; }}
    </style>
  </defs>
  <rect width="1200" height="630" fill="url(#background)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>

  <text x="64" y="55" class="eyebrow">OPENMULTIMODALLAB · FORMAL LOCAL COMPARISON</text>
  <text x="64" y="111" class="title">Quality and speed vs. memory</text>
  <text x="64" y="146" class="subtitle">Same tasks, prompts, protocol, commit, and RTX 4060 Laptop GPU</text>

  <circle cx="795" cy="142" r="7" fill="{qwen.color}"/>
  <text x="811" y="148" class="model">{qwen.label}</text>
  <circle cx="995" cy="142" r="7" fill="{smol.color}"/>
  <text x="1011" y="148" class="model">{smol.label}</text>

  <line x1="64" y1="178" x2="1136" y2="178" stroke="#27415c"/>

  <text x="64" y="224" class="metric">MEAN TASK SCORE ↑</text>
  <text x="1090" y="224" text-anchor="end" class="scale">0–1 · higher is better</text>
{qwen_score}
{smol_score}

  <text x="64" y="344" class="metric">MEDIAN TASK LATENCY ↓</text>
  <text x="1090" y="344" text-anchor="end" class="scale">0–450 ms · lower is better</text>
{qwen_latency}
{smol_latency}

  <text x="64" y="464" class="metric">PEAK ALLOCATED GPU MEMORY ↓</text>
  <text x="1090" y="464" text-anchor="end" class="scale">0–4,500 MiB · lower is better</text>
{qwen_memory}
{smol_memory}

  <line x1="64" y1="548" x2="1136" y2="548" stroke="#27415c"/>
  <circle cx="71" cy="572" r="5" fill="{qwen.color}"/>
  <text x="86" y="578" class="takeaway">Qwen: +{score_gap:.3f} score and {latency_reduction:.0f}% lower median latency</text>
  <circle cx="639" cy="572" r="5" fill="{smol.color}"/>
  <text x="654" y="578" class="takeaway">SmolVLM2: {memory_reduction:.0f}% lower peak memory</text>

  <text x="64" y="605" class="protocol">10 generated tasks · 1 warm-up + 3 measured repeats · greedy decoding · {qwen.successful_tasks}/{qwen.total_tasks} successful measurements each</text>
  <text x="1136" y="605" text-anchor="end" class="limit">SMALL SYNTHETIC SET · NOT A UNIVERSAL RANKING</text>
</svg>
"""


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    results_root = project_root / "docs" / "reports" / "results"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--qwen-result",
        type=Path,
        default=results_root / "2026-07-31-qwen3-vl-comparison-formal.jsonl",
    )
    parser.add_argument(
        "--smol-result",
        type=Path,
        default=(
            results_root
            / "2026-07-31-smolvlm2-500m-comparison-formal.jsonl"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "docs" / "assets" / "model-comparison.svg",
    )
    args = parser.parse_args()

    qwen = _load_result(
        args.qwen_result,
        label="Qwen3-VL-2B",
        color="#58b8ff",
    )
    smol = _load_result(
        args.smol_result,
        label="SmolVLM2-500M",
        color="#ffb45e",
    )
    svg = render_chart(qwen, smol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Generated comparison chart: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

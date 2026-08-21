# Suggested title

[Project] Reproducible VLM benchmarking on an 8 GB GPU — raw runs, failures,
TTFT, memory, and rebuildable reports

# Post draft

I wanted a more reliable answer to “which local VLM fits this task and this
GPU?” than a few successful screenshots, so I built OpenMultimodalLab, the
open-source benchmark engine behind AlvenX.

It runs versioned image, document, short-video, and robustness tasks through
local model adapters and keeps the task-level JSONL, failures, environment
manifest, timing, throughput, and peak allocated GPU memory. Reports are
derived artifacts and can be rebuilt without rerunning inference.

The v1.0 evidence set runs pinned Qwen3-VL-2B and
SmolVLM2-500M-Video-Instruct revisions on one RTX 4060 Laptop GPU (8,188 MiB):

- 102 licensed, human-checked tasks;
- 1 warm-up + 3 complete measured repetitions per model;
- 612 measured attempts, with the raw records committed;
- Qwen mean task score 0.784 vs. SmolVLM2 0.690;
- median TTFT 120.5 ms vs. 260.0 ms;
- peak allocated GPU memory 4,180.5 MiB vs. 1,265.3 MiB;
- zero runtime failures in the formal grid.

This is not a universal leaderboard. The corpus is controlled synthetic data,
the comparison currently covers only two small models, and results from one
GPU should not be transferred to another hardware profile without rerunning.

Repo and reproducible evidence:
<https://github.com/AlbertXXuu/OpenMultimodalLab>

I am specifically looking for clean-environment first-run feedback. If the
quick start fails or hides an assumption, please share the OS, GPU, Python
version, command, and redacted error. I would also value criticism of the
measurement protocol and suggestions for one next model that answers a
genuinely different low-VRAM question.

# Before posting

- Attach the committed comparison chart or short-video demo, not a new result.
- Recheck every number against the v1.0.0 report.
- Read the current community rules and avoid reposting the same copy elsewhere
  on the same day.
- Stay available to answer reproducibility questions after publishing.

# AlvenX v1.0: reproducible local VLM evidence on an 8 GB GPU

I built OpenMultimodalLab because model selection on consumer hardware is too
often reduced to isolated screenshots. The project runs versioned image,
document, short-video, and robustness tasks through interchangeable local VLM
adapters, then preserves the task-level outputs, failures, timing metadata, and
environment manifest needed to rebuild the report.

The first public evidence set compares pinned Qwen3-VL-2B and
SmolVLM2-500M-Video-Instruct revisions on the same NVIDIA RTX 4060 Laptop GPU:

- 102 licensed, human-checked tasks;
- one warm-up and three complete measured repetitions;
- 612 measured attempts and zero runtime failures;
- quality, TTFT, latency, throughput, and peak allocated GPU memory;
- raw JSONL and SHA-bound manifests committed alongside a byte-rebuildable
  report.

The result is a hardware/task trade-off, not a universal ranking: Qwen led the
aggregate score and median latency, while SmolVLM2 used about 70% less peak GPU
memory and led selected categories. All current media are controlled synthetic
assets, and only two small models are included.

If you have an 8 GB NVIDIA GPU, the most useful contribution is an independent
first run from a clean environment. Please report the operating system, GPU,
Python version, exact command, and the first blocker or surprising result. Do
not include private paths, tokens, or sensitive media.

Repository: <https://github.com/AlbertXXuu/OpenMultimodalLab>

Quick start:
<https://github.com/AlbertXXuu/OpenMultimodalLab#five-minute-core-quick-start>

What should the next evidence-backed comparison answer?

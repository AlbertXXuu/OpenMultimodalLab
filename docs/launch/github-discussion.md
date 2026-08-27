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

Within the pinned 102-task protocol and recorded RTX 4060 Laptop GPU, Qwen led
the aggregate score and median latency, while SmolVLM2 used about 70% less peak
GPU memory and led selected categories. The evidence set contains two small
models and controlled synthetic media.

If you try the workflow, useful feedback includes the operating system, GPU,
Python version, exact command, and the first confusing step or surprising
result. This helps improve setup, evidence readability, and model-adapter
integration. Do not include private paths, tokens, or sensitive media.

Repository: <https://github.com/AlbertXXuu/OpenMultimodalLab>

Quick start:
<https://github.com/AlbertXXuu/OpenMultimodalLab#five-minute-core-quick-start>

What should the next evidence-backed comparison answer?

# Measuring two local multimodal backends with reproducible boundaries

2026-10-02 · OpenMultimodalLab

[简体中文](multimodal-measurement.zh-CN.md) · [Website reading view](https://alvenx.com/notes/engineering/multimodal-measurement)

OpenMultimodalLab preserves 612 measured attempts across 102 tasks and two pinned models. The useful engineering result is a comparison that keeps task quality, compute timing, memory, interruption recovery, and evidence provenance distinct.

## A model comparison needs a defined experiment

A score alone cannot tell a reader which inputs, decoding settings, or hardware produced it. Timing also changes meaning when preprocessing, first token computation, and full task completion are mixed. OpenMultimodalLab addresses that problem with versioned tasks, explicit metric definitions, and preserved records rather than a standalone score chart.

The formal v1.0.0 evidence uses 102 unique human checked synthetic tasks across image, document, short video, and robustness datasets. Qwen3-VL-2B-Instruct and SmolVLM2-500M-Video-Instruct each complete three measured repetitions: 306 attempts per backend and 612 in total. One successful warm up per backend is stored separately and excluded from measured aggregates.

[Frozen formal report](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/v1.0.0-candidate/report.md)

## Pin inputs and keep quality separate from execution

Both backends ran on one NVIDIA RTX 4060 Laptop GPU with 8,188 MiB, batch size one, greedy decoding, no retries, and no reloads during measurement. Their model revisions are immutable: Qwen at 89644892e4d85e24eaac8bacfd4f463576704203 and SmolVLM2 at 7b375e1b73b11138ff12fe22c8f2822d8fe03467.

A successful attempt means inference and evaluation completed. It does not mean the answer was fully correct. The report therefore publishes runtime failures and deterministic task scores separately. On this grid, both backends had zero runtime failures; mean task scores were 0.784 and 0.690. Category results remain available because an aggregate can conceal different strengths.

| Pinned backend | Measured attempts | Mean task score | Median task latency | Peak allocated GPU memory |
| --- | --- | --- | --- | --- |
| Qwen3-VL-2B | 306 | 0.784 | 212.9 ms | 4,180.5 MiB |
| SmolVLM2-500M | 306 | 0.690 | 471.5 ms | 1,265.3 MiB |

[Protocol and metric definitions](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/evaluation-protocol.md) · [Published results and latency table](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/README.md)

## Define timing and memory at observable boundaries

The Transformers adapter synchronizes CUDA before generation and when the first generated token logits are available. TTFT covers that local compute interval: its medians are 120.5 ms for Qwen and 260.0 ms for SmolVLM2. Task latency measures the adapter invocation plus deterministic evaluation, so it includes work outside generation and has a different boundary.

Memory is torch.cuda.max_memory_allocated during generation after resetting peak statistics. It measures PyTorch allocated CUDA memory, not total process VRAM or the entire device peak. Throughput counts each model's native token IDs; different tokenizers make a cross family tokens per second ranking less informative than quality, latency, and failures.

[Timing and allocation implementation](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/src/openmultimodal_lab/adapters/transformers_image_text.py) · [Measurement boundaries](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/evaluation-protocol.md)

## Recovery and reports must preserve the same experiment

Each JSONL record is flushed and synced before an atomic manifest checkpoint records counts, bytes, and SHA-256. Strict resume checks dataset and media hashes, task order, model revision, generation settings, environment, and the exact prefix of the phase and repetition plan. A changed configuration, truncated final record, or mismatch with the manifest is rejected; recovery never guesses which rows to keep.

The report builder validates complete grids, clean source commits, model identity, input hashes, and JSONL sidecars before aggregation. Its bundle binds output and generator hashes and can be rebuilt from preserved results without another model call. The recorded result filenames carry August 10; their manifests retain the actual UTC execution timestamps separately. Article publication on October 2 does not imply a new benchmark run.

[Durable records and strict resume](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/run-records-and-manifests.md) · [Report source and grid validation](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/src/openmultimodal_lab/report_bundle.py) · [Qwen source manifest](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/results/2026-08-10-qwen3-vl-v1.0.0-formal.manifest.json) · [SmolVLM2 source manifest](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/results/2026-08-10-smolvlm2-v1.0.0-formal.manifest.json)

## A bounded comparison with inspectable evidence

These measurements apply to the preserved synthetic corpus, pinned models, recorded machine, and decoding settings. Three repetitions improve visibility into this experiment but do not establish a general model ranking or production quality. SHA-256 detects inconsistency while the manifest is trusted; it is not a signature against an actor who can rewrite both artifacts.

LMMs-Eval is a primary reference for reusable multimodal task and model evaluation. The narrower contribution here is making a small local comparison inspectable through declared boundaries, strict recovery, and report reconstruction. Its numbers are supported by the preserved OpenMultimodalLab records.

[LMMs-Eval primary repository](https://github.com/EvolvingLMMs-Lab/lmms-eval)

## Original evidence

- [Formal benchmark report](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/v1.0.0-candidate/report.md)
- [Measurement protocol](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/evaluation-protocol.md)
- [Record and resume contract](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/run-records-and-manifests.md)
- [Deterministic report builder](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/src/openmultimodal_lab/report_bundle.py)

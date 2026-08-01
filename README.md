# OpenMultimodalLab

[![CI](https://github.com/AlbertXXuu/OpenMultimodalLab/actions/workflows/ci.yml/badge.svg)](https://github.com/AlbertXXuu/OpenMultimodalLab/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

[简体中文](README.zh-CN.md)

A local-first, reproducible benchmark toolkit for answering a practical
question: **which vision-language model works best for this task and this
hardware, and what evidence supports that choice?**

OpenMultimodalLab runs versioned multimodal tasks through interchangeable model
adapters, preserves every output and failure as JSONL, applies deterministic
task-selected scoring, and records enough configuration and environment data
to rebuild a report without rerunning the model.

> Status: active pre-release development. Image, document, table, and chart
> tasks, two real local backends, the formal performance protocol, strict
> resume, bounded retries, cooperative inference deadlines, and CI quality
> gates work today. Both real adapters now decode local short video through a
> bounded eight-frame path. A formal 32-task document comparison is preserved
> below; the licensed video task set and formal video comparison remain
> roadmap work.

## First reproducible comparison

One NVIDIA RTX 4060 Laptop GPU (8,188 MiB), the same ten project-generated
tasks, one warm-up, three measured repetitions, greedy decoding, batch size 1,
and one clean Git commit:

| Model | Mean task score | Median TTFT | Median task latency | Peak allocated GPU memory | Runtime failures |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL-2B | 1.000 | 107.4 ms | 182.8 ms | 4,093.3 MiB | 0/30 |
| SmolVLM2-500M | 0.733 | 257.6 ms | 386.7 ms | 1,265.3 MiB | 0/30 |

The result is a resource-versus-quality observation, not a universal model
ranking. SmolVLM2 used about 69% less peak allocated memory, while Qwen
produced more complete answers and lower median latency on this small task
mix. Model sizes and native visual processors differ, and the ten synthetic
English tasks do not represent broad real-world capability.

![Formal Qwen3-VL-2B and SmolVLM2-500M comparison](docs/assets/model-comparison.svg)

Read the [full comparison](docs/reports/2026-07-31-qwen3-vl-vs-smolvlm2.md)
or inspect the preserved
[Qwen JSONL](docs/reports/results/2026-07-31-qwen3-vl-comparison-formal.jsonl),
[SmolVLM2 JSONL](docs/reports/results/2026-07-31-smolvlm2-500m-comparison-formal.jsonl),
and their manifests.

## Broader document benchmark

The same two backends also completed all 96 measured attempts on 32 OCR,
key-value, table, and chart tasks:

| Model | Mean task score | Median TTFT | Median task latency | Peak allocated GPU memory | Runtime failures |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL-2B | 0.719 | 184.2 ms | 353.3 ms | 4,180.4 MiB | 0/96 |
| SmolVLM2-500M | 0.625 | 307.6 ms | 565.4 ms | 1,265.3 MiB | 0/96 |

Qwen was stronger overall and on table/chart questions. SmolVLM2 achieved
`1.000` on the OCR subset and used about 70% less peak allocated memory. All
32 responses/model were stable across three repetitions. This remains a
generated English benchmark, not a general document-understanding ranking.

![Formal document-task comparison](docs/assets/document-comparison.svg)

Read the [document comparison report](docs/reports/2026-08-02-document-model-comparison.md)
or inspect the preserved
[Qwen JSONL](docs/reports/results/2026-08-02-qwen3-vl-docs-formal.jsonl),
[SmolVLM2 JSONL](docs/reports/results/2026-08-02-smolvlm2-500m-docs-formal.jsonl),
and their manifests.

## What is already implemented

- A dependency-free core and deterministic `mock` backend for offline CI.
- Real, lazy-loaded Qwen3-VL-2B and SmolVLM2-500M Transformers backends.
- Immutable model revisions and native processor/chat-template metadata.
- Versioned UTF-8 JSONL tasks with validation and licensed generated media.
- Exact-match, numeric-tolerance, keyword-coverage, and ordered/unordered
  attribute-group scoring through backward-compatible task schemas 1.0–1.2.
- `synthetic-docs-v1`: 32 licensed tasks over eight reproducible OCR,
  key-value, table, bar-chart, and line-chart images.
- A shared local-video path for both real backends: PyAV decoding, eight
  uniformly sampled frames, preserved sampling metadata, and no hidden
  processor resampling. The formal licensed video dataset is not yet present.
- Name-neutral deterministic tooling can generate and hash-bind a 24-task
  short-video draft for human review; canonical dataset output still waits for
  owner naming approval.
- Warm-up plus repeated measurement with CUDA-synchronized TTFT, generation
  time, throughput, preprocessing time, and peak allocated memory.
- Typed model-load, timeout, out-of-memory, generation, and evaluation failures.
- Run record schema 0.4 with durable invocation indexes, terminal/retryable
  state, cumulative latency, retry policy, and cooperative deadlines.
- Strict `--resume`, explicit `--overwrite`, output SHA-256, and atomic
  per-record checkpoints.
- Backend-aware `doctor` checks for Python, CUDA, BF16, optional packages, and
  available working/model-cache disk without printing the cache path.
- Bounded local input parsing for dataset/result JSONL, images, and short video,
  plus portable media references and path-redacted durable errors.
- Python 3.11/3.12 Linux CI, wheel builds, link/JSON/privacy checks, and
  an offline test suite.

## Architecture

```mermaid
flowchart LR
    A["Versioned task JSONL"] --> B["Loader + validator"]
    B --> C["Benchmark runner"]
    C --> D["Model adapter"]
    D --> E["Local VLM"]
    D --> C
    C --> F["Task-selected scorer"]
    C --> G["Durable JSONL + manifest"]
    G --> H["Reporter"]
    H --> I["Rebuilt summary / comparison"]
```

Inference and reporting are deliberately separate. Charts and summaries are
derived artifacts; raw task-level evidence remains the source of truth.

## Five-minute core quick start

The core path does not download a model and works on Python 3.11, 3.12, or
3.13. The primary examples use Windows PowerShell:

```powershell
git clone https://github.com/AlbertXXuu/OpenMultimodalLab.git
cd OpenMultimodalLab

py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .

.\.venv\Scripts\oml.exe doctor
.\.venv\Scripts\oml.exe run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/smoke-001.jsonl
.\.venv\Scripts\oml.exe report `
  --input runs/smoke-001.jsonl
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux uses the same CLI arguments with POSIX environment paths:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/oml doctor
.venv/bin/oml run \
  --dataset examples/tasks/smoke.jsonl \
  --output runs/smoke-001.jsonl
.venv/bin/oml report --input runs/smoke-001.jsonl
.venv/bin/python -m unittest discover -s tests -v
```

The `mock` backend verifies infrastructure only. Do not use its score as a
model-quality result.

## Run a real local model

Use a separate Python 3.11 or 3.12 environment. Install a CUDA-enabled PyTorch
build appropriate for your platform before the project extra; `doctor`
detects a CPU-only mismatch when an NVIDIA GPU is visible.

- [Qwen3-VL installation and verified Windows profile](docs/backends/qwen3-vl.md)
- [SmolVLM2 installation and verified profile](docs/backends/smolvlm2.md)

Example after the Qwen environment is ready:

```powershell
.\.venv-ml\Scripts\oml.exe doctor --backend qwen3-vl

.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-formal-001.jsonl
```

The first real run downloads the pinned model into the Hugging Face user
cache. Model weights and raw `runs/` outputs are excluded from Git.

## Safe output and recovery

`oml run` refuses to replace an existing output or manifest. After a compatible
interruption, repeat the exact command with `--resume`:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-formal-001.jsonl `
  --resume
```

Resume verifies dataset/media hashes, tasks and order, model revision,
generation settings, environment, Git state, output hash and size, record
count, and the exact attempt prefix before appending anything. Use
`--overwrite` only when replacing the old evidence is intentional.

See the [strict resume report](docs/reports/2026-07-31-resumable-runs.md) for
the crash-consistency model and failure-injection evidence.

For long local runs, bounded retry and timeout policy is explicit:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-docs-v1.jsonl `
  --attempt-timeout-seconds 120 `
  --max-retries 1 `
  --output runs/qwen3-vl-docs-001.jsonl
```

Retries apply only to `timeout` and `generation_error`; invalid input, model
load failure, and out-of-memory are terminal. Built-in model deadlines are
cooperative and begin after one-time model loading. They can bound preprocessing
and Transformers generation, but cannot safely preempt a running CUDA kernel.

## Reproducibility contract

A publishable run should:

1. use immutable task and model revisions;
2. preserve the stored prompts and semantic media;
3. use deterministic decoding and batch size 1;
4. perform at least one warm-up and three measured repetitions;
5. retain slow attempts and failures;
6. publish raw JSONL, the manifest, metric definitions, and limitations.

The [evaluation protocol](docs/evaluation-protocol.md) defines timing and
comparison boundaries. Cross-model token throughput is not treated as directly
equivalent because tokenizers differ.

## Evidence and documentation

| Topic | Document |
|---|---|
| Project objective and acceptance criteria | [Goals and success](docs/01-goals-and-success.md) |
| Scope and requirements | [Scope](docs/02-scope-and-requirements.md) |
| System design | [Architecture](docs/03-architecture.md) |
| Experiment rules | [Evaluation protocol](docs/evaluation-protocol.md) |
| Run records, manifests, and resume | [Artifact contract](docs/run-records-and-manifests.md) |
| Two-model formal result | [Qwen3-VL vs SmolVLM2](docs/reports/2026-07-31-qwen3-vl-vs-smolvlm2.md) |
| 32-task document comparison | [Qwen3-VL vs SmolVLM2 on documents](docs/reports/2026-08-02-document-model-comparison.md) |
| Performance methodology | [Qwen formal performance baseline](docs/reports/2026-07-31-qwen3-vl-formal-performance.md) |
| Quality and public-release gates | [Quality standard](docs/06-quality-and-open-source.md) |
| Live public-release status | [Evidence matrix and strict readiness check](docs/public-release-readiness.md) |
| Real short-video runtime smoke | [Two-backend Windows GPU evidence](docs/reports/2026-08-02-video-runtime-smoke.md) |
| Short-video corpus tooling | [Deterministic generation and human-review workflow](docs/video-corpus-tooling.md) |
| Fresh wheel installation | [Windows audit and permanent CI gate](docs/reports/2026-08-01-fresh-wheel-install.md) |
| Dependency supply chain | [Action pinning and update audit](docs/reports/2026-08-01-supply-chain-audit.md) |
| Security review | [Bounded local-input and privacy audit](docs/reports/2026-08-02-security-review.md) |
| Document/table/chart task set | [`synthetic-docs-v1` evidence report](docs/reports/2026-08-01-synthetic-docs-v1.md) |
| Timeout and retry provenance | [Run record schema 0.4 report](docs/reports/2026-08-01-run-record-0.4.md) |
| First complete experiment | [Step-by-step tutorial](docs/tutorials/first-reproducible-benchmark.md) |
| Current work | [Task board](TASKS.md) |
| Third-party licenses | [Third-party notices](THIRD_PARTY_NOTICES.md) |

## Project status

| Area | Current state |
|---|---|
| Real image backends | Qwen3-VL-2B and SmolVLM2-500M verified locally |
| Current versioned task corpus | 42 tasks over 18 licensed, deterministic generated images |
| Preserved real-model comparison | 10 image tasks plus a separate 32-task document/table/chart comparison |
| Performance protocol | Warm-up, three repetitions, TTFT, throughput, latency, peak memory |
| Reliability | Durable records, strict resume, integrity hashes, typed failures |
| Automated quality | Offline tests, Python 3.11/3.12 CI, repository audit, fresh-wheel smoke test |
| Next capability work | Licensed short-video task set and formal two-model run |

The target is at least 100 human-checked tasks across image, document, chart,
spatial, and short-video capabilities. That target is not yet marked complete.

## Contributing

Small, testable contributions that improve reproducibility are welcome.
Before proposing another model, include its exact revision, license,
installation path, verified hardware, adapter contract tests, and known
limitations.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_repository.py
.\.venv\Scripts\python.exe scripts/check_release_readiness.py
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the full checklist.
Sensitive vulnerabilities follow [SECURITY.md](SECURITY.md), not a public bug
report.

## License

Project code and project-generated synthetic media use Apache-2.0. Model
weights and optional runtime dependencies retain their own licenses and are
not distributed in this repository. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This project does not promise a Star count or present planned users as real
adoption. Reproducible evidence, usable documentation, and external feedback
are the measures that matter.

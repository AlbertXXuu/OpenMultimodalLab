# Tutorial: Your First Reproducible Multimodal Benchmark

This tutorial starts with the offline `mock` backend, explains every artifact,
then shows how to replace it with a real local model without changing the task
or reporting pipeline.

The mock result proves that the infrastructure works. It does not measure
model quality.

## 1. Prerequisites

- Windows PowerShell;
- Git;
- Python 3.11 or 3.12 for the documented path;
- about five minutes for the core tutorial;
- no GPU or model download for sections 1–6.

Clone and enter the repository:

```powershell
git clone https://github.com/AlbertXXuu/OpenMultimodalLab.git
cd OpenMultimodalLab
```

Create an isolated environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Check the core runtime:

```powershell
.\.venv\Scripts\oml.exe doctor
```

Expected final line:

```text
Status: core runtime ready.
```

## 2. Inspect the task file

The smoke dataset is newline-delimited JSON:

```powershell
Get-Content examples/tasks/smoke.jsonl
```

Each non-empty line is one task object. Important fields are:

- `schema_version`: parser contract used for the task;
- `id`: stable unique task identity;
- `prompt`: exact text sent to the backend;
- `media`: zero or more repository-relative media paths;
- `expected_keywords` and `scoring`: deterministic evaluation contract;
- `metadata`: dataset version, category, language, provenance, and license.

The loader validates the complete dataset before model inference starts. It
rejects duplicate IDs, unsupported schemas, malformed scoring rules, and
missing media with a source line and task ID.

## 3. Run the offline benchmark

Choose a new output path:

```powershell
.\.venv\Scripts\oml.exe run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/tutorial-smoke-001.jsonl
```

The command prints a summary and creates:

```text
runs/tutorial-smoke-001.jsonl
runs/tutorial-smoke-001.jsonl.manifest.json
```

The JSONL contains one durable record per attempted task. The neighboring
manifest identifies the complete experiment.

## 4. Inspect the raw evidence

Read task-level records:

```powershell
Get-Content runs/tutorial-smoke-001.jsonl
```

Every record includes:

- phase and repetition;
- task, dataset, backend, and model revision;
- timestamp, status, response, latency, and error;
- metric name, score, matched references, and metric details;
- media paths and optional backend usage metrics.

Read the manifest:

```powershell
Get-Content `
  runs/tutorial-smoke-001.jsonl.manifest.json
```

The manifest contains:

- dataset and media SHA-256 values;
- selected task IDs, categories, and order;
- backend, revision, and generation settings;
- Python, packages, platform, GPU, and Git state;
- output status, record counts, byte length, and SHA-256.

Verify the output independently:

```powershell
$manifest = Get-Content -Raw `
  runs/tutorial-smoke-001.jsonl.manifest.json |
  ConvertFrom-Json

$actual = (Get-FileHash -Algorithm SHA256 `
  runs/tutorial-smoke-001.jsonl).Hash.ToLowerInvariant()

$manifest.output.sha256 -eq $actual
```

Expected result:

```text
True
```

## 5. Rebuild the report

The reporter reads the JSONL, not the original model:

```powershell
.\.venv\Scripts\oml.exe report `
  --input runs/tutorial-smoke-001.jsonl
```

Request machine-readable output:

```powershell
.\.venv\Scripts\oml.exe report `
  --input runs/tutorial-smoke-001.jsonl `
  --json
```

This separation matters: a report formatting bug can be fixed and the summary
rebuilt without paying for inference again.

For a formal multi-model comparison, use the stricter bundle builder. Unlike
the single-run summary, it requires at least two backends, identical task
grids, exactly one warm-up and three repeats, clean manifests, immutable model
identities, and matching dataset/media hashes:

```powershell
.\.venv\Scripts\python.exe scripts\build_benchmark_report.py `
  --input docs/reports/results/2026-07-31-qwen3-vl-comparison-formal.jsonl `
  --input docs/reports/results/2026-07-31-smolvlm2-500m-comparison-formal.jsonl `
  --output-dir runs/tutorial-formal-report

.\.venv\Scripts\python.exe scripts\build_benchmark_report.py `
  --verify `
  --output-dir runs/tutorial-formal-report
```

The six-file output contract and final-release workflow are documented in
[Deterministic report bundles](../report-bundles.md).

## 6. Verify safe output behavior

Repeat the original run command without another flag:

```powershell
.\.venv\Scripts\oml.exe run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/tutorial-smoke-001.jsonl
```

Expected behavior:

- exit code 2;
- message that the output or manifest already exists;
- original output remains unchanged.

Use a new output path for an independent experiment. Use `--overwrite` only
when replacement is deliberate. Use `--resume` only after an interrupted run
with exactly the same inputs, model, environment, and protocol.

## 7. Run repository validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_repository.py
```

The repository check validates text hygiene, local links, JSON/JSONL, common
credential patterns, private-key headers, and personal paths. GitHub CI repeats
these checks on Linux and builds the wheel.

## 8. Replace mock with Qwen3-VL

This section requires an NVIDIA-compatible Python 3.11/3.12 environment and a
CUDA-enabled PyTorch build. Follow the
[Qwen3-VL backend guide](../backends/qwen3-vl.md) first.

Check the real runtime:

```powershell
.\.venv-ml\Scripts\oml.exe doctor --backend qwen3-vl
```

Start with one constrained task:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --category visual-comparison `
  --max-new-tokens 32 `
  --output runs/tutorial-qwen-single-001.jsonl
```

For a protocol-compliant performance run:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/tutorial-qwen-formal-001.jsonl
```

Formal status requires exactly one successful warm-up, exactly three complete
task-grid repetitions, complete performance fields for successful attempts,
recorded errors for failed attempts, no retries, and no measurement-phase
model reload.

## 9. Compare without overstating

Run SmolVLM2 with the same dataset, prompt text, token limit, warm-up, and
repetitions after following its
[backend guide](../backends/smolvlm2.md).

Compare:

- deterministic task score and failure categories;
- median and p95 task latency;
- median TTFT and generation time;
- peak allocated GPU memory;
- model and processor input metadata.

Do not interpret cross-model token IDs per second as equivalent natural
language tokens. Do not call ten synthetic tasks a broad leaderboard. Record
model-size and native-preprocessing differences.

The repository's
[first formal comparison](../reports/2026-07-31-qwen3-vl-vs-smolvlm2.md)
shows the expected evidence and limitation style.

## 10. What this demonstrates in an interview

A concise five-minute explanation can cover:

1. **Problem:** multimodal model choices are often based on anecdotes rather
   than reproducible task/hardware evidence.
2. **Architecture:** versioned tasks, interchangeable adapters, deterministic
   scorers, durable records, manifests, and report reconstruction.
3. **Systems work:** CUDA timing boundaries, native processors, immutable
   revisions, crash-safe checkpoints, and strict recovery.
4. **Evidence:** preserved raw runs and a two-model quality/latency/memory
   trade-off.
5. **Engineering judgment:** explicit limitations, licenses, CI, and refusal
   to turn a small synthetic set into an inflated claim.

That story is more valuable than quoting only the final score because it shows
how trustworthy evidence was produced.

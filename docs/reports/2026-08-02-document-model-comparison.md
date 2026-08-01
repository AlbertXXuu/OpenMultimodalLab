# Qwen3-VL-2B vs SmolVLM2-500M on document tasks

Date: 2026-08-02

## Result

On all 32 tasks in `synthetic-docs-v1`, Qwen3-VL-2B achieved a mean
deterministic score of `0.719`; SmolVLM2-500M achieved `0.625`. Both models
completed all 96 measured attempts without runtime failures, and every task
produced the same response in all three repetitions.

Qwen had the stronger aggregate quality, lower median time to first token
(TTFT), and lower median end-to-end latency. SmolVLM2 used `1,265.3 MiB` of
peak allocated GPU memory versus Qwen's `4,180.4 MiB`, a reduction of about
70%. SmolVLM2 also scored `1.000` on document OCR, while Qwen was stronger on
the table and chart subsets.

This is a quality-versus-resource observation on clean, English, generated
documents. It is not a universal model ranking, a same-size architecture
comparison, or evidence about arbitrary real-world scans.

![Formal document-task quality, latency, and memory comparison](../assets/document-comparison.svg)

The visual is regenerated directly from the preserved JSONL:

```powershell
.\.venv\Scripts\python.exe scripts\generate_comparison_chart.py `
  --qwen-result docs/reports/results/2026-08-02-qwen3-vl-docs-formal.jsonl `
  --smol-result docs/reports/results/2026-08-02-smolvlm2-500m-docs-formal.jsonl `
  --output docs/assets/document-comparison.svg
```

Automated tests require the regenerated SVG to match the committed file
byte-for-byte.

## Formal protocol

Both configurations used:

- the same clean Git commit: `2ba683fe0d3cff65e502ae9e9f5d559d180b5398`;
- the same immutable `synthetic-docs-v1` JSONL, 32 task IDs, and eight
  byte-identical project-generated PNGs;
- deterministic decoding with `do_sample=false`, batch size 1, and
  `max_new_tokens=64`;
- one successful warm-up followed by three measured repetitions in fixed
  dataset order;
- no retries and no attempt timeout;
- the same Windows machine, Python 3.11 environment, CUDA runtime, and package
  versions;
- each model's pinned native processor and chat template.

Both manifests record `dirty=false`, `status=completed`, the same task/media
hashes, 97 total records, and 96 measurement records. Model loading occurred
only during warm-up: no measurement record has a positive `model_load_ms`.

## Environment

| Field | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8,188 MiB |
| Driver | 596.49 |
| OS | Windows 11 (`Windows-10-10.0.26200-SP0`) |
| Python | CPython 3.11.0 |
| PyTorch | 2.13.0+cu130 |
| Transformers | 5.14.1 |
| Accelerate | 1.14.0 |
| PyAV | 18.0.0 |
| Qwen checkpoint | `Qwen/Qwen3-VL-2B-Instruct` at `89644892e4d85e24eaac8bacfd4f463576704203` |
| Smol checkpoint | `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` at `7b375e1b73b11138ff12fe22c8f2822d8fe03467` |
| Effective dtype | BF16 for both models |

## Quality

| Model | Mean score | Median score | Successful measurements | Runtime failures | Stable tasks |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL-2B | 0.719 | 1.000 | 96/96 | 0 | 32/32 |
| SmolVLM2-500M | 0.625 | 1.000 | 96/96 | 0 | 32/32 |

Category means expose where the aggregate difference came from:

| Category | Unique tasks | Attempts/model | Qwen3-VL-2B | SmolVLM2-500M |
|---|---:|---:|---:|---:|
| Document OCR | 6 | 18 | 0.833 | 1.000 |
| Document key-value | 10 | 30 | 0.900 | 0.900 |
| Table QA | 8 | 24 | 0.500 | 0.250 |
| Chart QA | 8 | 24 | 0.625 | 0.375 |

The result separates inference reliability from answer quality: both runtimes
were 100% successful, but deterministic task contracts still caught incorrect
OCR, lookup, arithmetic, and chart-reading answers. Because each task's three
responses were identical, repetition measured runtime variance rather than
sampling variance.

## Performance

Warm-up is excluded from every aggregate except model-load time.

| Metric | Qwen3-VL-2B | SmolVLM2-500M |
|---|---:|---:|
| Mean task latency | 471.5 ms | 596.4 ms |
| Median task latency | 353.3 ms | 565.4 ms |
| P95 task latency | 722.2 ms | 835.2 ms |
| Median preprocessing | 13.8 ms | 104.8 ms |
| Median TTFT | 184.2 ms | 307.6 ms |
| P95 TTFT | 209.9 ms | 327.5 ms |
| Median generation | 335.0 ms | 451.9 ms |
| Median generated IDs/s | 12.3 | 11.2 |
| Median decode IDs/s | 20.2 | 28.4 |
| Peak allocated GPU memory | 4,180.4 MiB | 1,265.3 MiB |
| Warm-up model load | 14,048.2 ms | 18,306.3 ms |
| Measurement model reloads | 0 | 0 |

Interpretation:

- Qwen's median TTFT was about 40% lower and its median task latency about 38%
  lower on this task mix.
- SmolVLM2 reduced peak allocated memory by about 70%, leaving more headroom on
  an 8 GB GPU.
- The smaller model was not faster here. Its native image-splitting processor
  produced a median of 885.5 input token IDs, versus 408 for Qwen, and its
  median preprocessing time was about 7.6 times higher.
- Generated IDs/s and decode IDs/s are not directly comparable across model
  families because tokenizers differ. They remain useful for repeated runs of
  the same pinned configuration.

## Reproduction

After preparing the verified Python 3.11 CUDA environment:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-docs-v1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-synthetic-docs-v1-formal.jsonl

.\.venv-ml\Scripts\oml.exe run `
  --backend smolvlm2 `
  --dataset examples/tasks/synthetic-docs-v1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/smolvlm2-synthetic-docs-v1-formal.jsonl
```

Rebuild either summary without loading a model:

```powershell
.\.venv\Scripts\oml.exe report `
  --input docs/reports/results/2026-08-02-qwen3-vl-docs-formal.jsonl

.\.venv\Scripts\oml.exe report `
  --input docs/reports/results/2026-08-02-smolvlm2-500m-docs-formal.jsonl
```

## Preserved evidence

| Artifact | SHA-256 |
|---|---|
| [Qwen raw JSONL](results/2026-08-02-qwen3-vl-docs-formal.jsonl) | `1B0655EE19C1CD6C635A15D66ABE90BC4F44BB06EDDA8E13EFA808F27BE2AC17` |
| [Qwen manifest](results/2026-08-02-qwen3-vl-docs-formal.manifest.json) | `38AEE214B5288F14AC5E0BC8FBCF9F8CAB9A332C93E6321B48485F8A1DFFF60E` |
| [Smol raw JSONL](results/2026-08-02-smolvlm2-500m-docs-formal.jsonl) | `63C979BE02E3E99400C45B4ECF8D2CA797B5EAEC0FF512B23FDED5F7D50471DF` |
| [Smol manifest](results/2026-08-02-smolvlm2-500m-docs-formal.manifest.json) | `F61E5FA8C4690A97119E6185F82212C739A78604170100420E3F7186F8567B2A` |

## Evidence hygiene

An earlier Qwen attempt was interrupted by an external process timeout. Its
strictly resumed JSONL remained structurally valid, but the replacement
process loaded the model during a measurement phase. That run was rejected
instead of being used as formal performance evidence. The accepted Qwen and
SmolVLM2 runs above each completed in one uninterrupted model process.

The reporter now refuses to label a run as formal when any measurement record
contains a positive `model_load_ms`. This guards future reports against the
same process-restart confound.

## Limitations

- All 32 tasks use eight clean, high-contrast, English synthetic images. The
  set does not represent photographed receipts, handwriting, blur, rotation,
  multilingual text, dense PDFs, or adversarial charts.
- Models differ by about four times in parameter count and use different
  native visual processors.
- Deterministic scoring checks declared short-answer contracts; it does not
  measure prose quality, broad factuality, or human preference.
- `peak_gpu_memory_mb` is PyTorch maximum allocated memory during generation,
  not total system GPU usage.
- Model-load time uses an already populated local cache and is not a download
  benchmark.

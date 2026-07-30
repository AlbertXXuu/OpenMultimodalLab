# Qwen3-VL-2B Formal Local Performance Baseline

Date: 2026-07-31 (Asia/Shanghai)

## Outcome

Qwen3-VL-2B-Instruct completed the first protocol-compliant local performance
run in OpenMultimodalLab:

- 1 recorded, unscored warm-up;
- 10 fixed-order tasks repeated 3 times;
- 30/30 successful measured attempts;
- 0 runtime or evaluation failures;
- mean and median structured score: 1.000;
- all three responses for every task were identical.

This replaces the earlier single-run latency numbers as the valid performance
baseline for this model and dataset. It does not establish a model comparison
because a second backend has not yet been measured.

## Reproducibility identity

| Item | Value |
|---|---|
| Code commit | `92c2ae7f58eaf36de7c3e2833a1ce191be3b284e` |
| Git dirty state | `false` |
| Dataset | `synthetic-v1.1` |
| Dataset SHA-256 | `682e4089fc2f9793209b40beb0026279bd0f58d3ec4fcf75d3f65abba88e4692` |
| Model | `Qwen/Qwen3-VL-2B-Instruct` |
| Model revision | `89644892e4d85e24eaac8bacfd4f463576704203` |
| Device / dtype | `cuda:0` / `torch.bfloat16` |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8,188 MiB |
| Driver | 596.49 |
| Python | 3.11.0 |
| PyTorch / CUDA build | 2.13.0+cu130 / CUDA 13.0 |
| Transformers | 5.14.1 |
| Batch / sampling | 1 / greedy, `do_sample=false` |
| Maximum new tokens | 64 |

The manifest hashes all ten media files and contains the full package list,
platform, task order, timing definitions, and durable record counts.

## Command

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-synthetic-v1.1-formal.jsonl
```

## Overall measurements

| Metric | Result |
|---|---:|
| Formal protocol check | yes |
| Measured attempts | 30 |
| Success rate | 100.0% |
| Mean / median score | 1.000 / 1.000 |
| Mean end-to-end latency | 521.644 ms |
| Median end-to-end latency | 203.857 ms |
| P95 end-to-end latency | 2,288.403 ms |
| Median preprocessing | 4.612 ms |
| Median TTFT | 114.397 ms |
| P95 TTFT | 136.375 ms |
| Median generation time | 197.278 ms |
| Median generated-ID throughput | 12.513 token IDs/s |
| Median decode-only throughput | 18.344 token IDs/s |
| Peak allocated CUDA memory | 4,093.285 MiB |
| Warm-up model load | 12,157.196 ms |

Warm-up values are preserved in the raw records but excluded from all measured
score, latency, throughput, and failure aggregates.

## Results by category

| Category | Attempts | Mean score | Median latency | P95 latency | Median TTFT |
|---|---:|---:|---:|---:|---:|
| Image description | 6 | 1.000 | 1,761.120 ms | 2,333.974 ms | 113.379 ms |
| Spatial reasoning | 12 | 1.000 | 208.609 ms | 371.059 ms | 114.241 ms |
| Counting | 9 | 1.000 | 177.104 ms | 218.485 ms | 116.148 ms |
| Visual comparison | 3 | 1.000 | 186.418 ms | 204.038 ms | 114.587 ms |

## Results by task

Each row is the median of three measured repetitions.

| Task | Score | Latency | TTFT | Output IDs | Output throughput |
|---|---:|---:|---:|---:|---:|
| `shapes-basic-001` | 1.000 | 2,288.403 ms | 112.712 ms | 61 | 26.744 IDs/s |
| `spatial-above-001` | 1.000 | 365.233 ms | 116.866 ms | 7 | 19.602 IDs/s |
| `counting-circles-001` | 1.000 | 177.104 ms | 125.826 ms | 2 | 11.812 IDs/s |
| `counting-squares-001` | 1.000 | 186.225 ms | 116.148 ms | 2 | 11.130 IDs/s |
| `spatial-left-001` | 1.000 | 177.153 ms | 110.413 ms | 2 | 11.666 IDs/s |
| `spatial-below-001` | 1.000 | 195.188 ms | 118.837 ms | 2 | 10.698 IDs/s |
| `shapes-multi-001` | 1.000 | 1,234.388 ms | 114.045 ms | 31 | 25.249 IDs/s |
| `counting-rectangles-001` | 1.000 | 155.094 ms | 95.015 ms | 2 | 13.543 IDs/s |
| `spatial-between-001` | 1.000 | 214.743 ms | 111.615 ms | 3 | 14.308 IDs/s |
| `comparison-size-001` | 1.000 | 186.418 ms | 114.587 ms | 2 | 11.056 IDs/s |

## Interpretation

TTFT is relatively stable across task categories. Most end-to-end variance
comes from output length: the two descriptive tasks generate 31 and 61 token
IDs, while constrained tasks generate only two or three. Reporting a single
mean latency without output length would therefore be misleading.

The warm-up successfully isolates the 12.157-second processor and weight load
from measured task latency. Peak allocated GPU memory is about 4.0 GiB, which
shows this checkpoint is viable on the tested 8GB GPU, but it is not the same
as total reserved VRAM or system-wide GPU use.

## Evidence

- [Raw JSONL records](results/2026-07-31-qwen3-vl-synthetic-v1-1-formal.jsonl)
- [Run manifest](results/2026-07-31-qwen3-vl-synthetic-v1-1-formal.manifest.json)

Preserved artifact SHA-256 values:

```text
raw JSONL: AAB9967307C2DC562759A47F1DA0719AA964911C8CD1F75E70F6D42767154067
manifest:  A20E65E7ADB30987022D524D651B90EECEAAF9ED522F6038FBFD06ED591FCAED
```

## Limits

- The ten tasks are deliberately simple synthetic images.
- Three repetitions quantify short-run variation, not long-duration thermal or
  power-state variation on a laptop GPU.
- TTFT marks synchronized first-token logits completion inside Transformers;
  it is not UI rendering or network streaming latency.
- Generated-ID throughput includes terminal special tokens.
- Peak memory is PyTorch CUDA allocated memory, not reserved memory.
- Only one model is included, so no claim about relative model quality or
  efficiency is made.

## Next decision

Select a second model family that runs on the same 8GB machine, implement the
same metric contract, and run the identical manifest protocol before producing
the first fair comparison.

# Qwen3-VL-2B First Real Baseline

Date: 2026-07-30

## Outcome

OpenMultimodalLab ran its first real local vision-language model on the full
ten-task `synthetic-v1` image set.

- Completed tasks: 10/10
- Runtime failures: 0
- Keyword mean score: 0.800
- Recorded mean latency: 2,504.230 ms
- Recorded p95 latency: 16,037.836 ms

This is an engineering baseline, not a publishable model comparison. It has no
warm-up, includes model loading in the first task, and has only one repetition.

The preserved raw records are in
[`results/2026-07-30-qwen3-vl-synthetic-v1.jsonl`](results/2026-07-30-qwen3-vl-synthetic-v1.jsonl).

## Repository review before implementation

The pre-change repository passed:

- all 11 existing unit tests;
- bytecode compilation;
- `git diff --check`;
- wheel construction;
- local Markdown target validation;
- the latest GitHub Actions run on Python 3.11 and 3.12.

No virtual environments, model weights, caches, or `runs/` outputs were tracked
by Git. The review identified two blockers for a real backend: the CLI always
constructed `MockAdapter`, and `doctor` could not distinguish an NVIDIA GPU
from a CPU-only PyTorch installation.

## Model decision

The default model is
[`Qwen/Qwen3-VL-2B-Instruct`](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)
at immutable revision:

```text
89644892e4d85e24eaac8bacfd4f463576704203
```

The 3.96GB checkpoint uses Apache-2.0 and is supported directly by
Transformers. It was selected over:

- [SmolVLM2-2.2B-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct),
  which is efficient and remains a useful comparison candidate but is older
  and primarily English-focused;
- [Gemma 3 4B](https://huggingface.co/google/gemma-3-4b-it), which requires
  accepting additional model terms before downloading;
- [DeepSeek-VL2](https://github.com/deepseek-ai/DeepSeek-VL2), whose official
  native examples target much larger VRAM even for the tiny/small family;
- [Janus-Pro](https://github.com/deepseek-ai/Janus), whose 1B checkpoint is a
  plausible second backend but requires DeepSeek-specific integration and a
  separate model license.

## Environment

| Component | Value |
|---|---|
| Operating system | Windows 11 build 26200 |
| Python | 3.11.0 |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU |
| VRAM | 8,188 MiB |
| NVIDIA driver | 596.49 |
| PyTorch | 2.13.0+cu130 |
| Torchvision | 0.28.0+cu130 |
| Transformers | 5.14.1 |
| Accelerate | 1.14.0 |
| Pillow | 12.3.0 |
| Device/dtype | `cuda:0` / `torch.bfloat16` |

The CUDA environment was verified with a real GPU tensor operation before model
inference.

## Run configuration

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.jsonl `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-synthetic-v1.jsonl
```

The adapter used batch size 1, `do_sample=false`, the task prompt without
manual rewriting, and the pinned model/processor revision above.

## Per-task result

| Task | Score | Latency ms | Observation |
|---|---:|---:|---|
| `shapes-basic-001` | 0.000 | 16,037.8 | Semantically correct; phrase matcher missed separated color/shape wording |
| `spatial-above-001` | 0.333 | 318.5 | Correct relation and shapes, but response omitted colors required only by references |
| `counting-circles-001` | 1.000 | 192.3 | Correct |
| `counting-squares-001` | 1.000 | 181.4 | Correct |
| `spatial-left-001` | 1.000 | 180.8 | Correct |
| `spatial-below-001` | 1.000 | 211.2 | Correct |
| `shapes-multi-001` | 0.667 | 1,612.4 | Model said green square; generated asset is 60×60 although reference says rectangle |
| `counting-rectangles-001` | 1.000 | 201.5 | Correct |
| `spatial-between-001` | 1.000 | 3,269.0 | Correct phrase appeared before output truncation |
| `comparison-size-001` | 1.000 | 2,837.3 | Correct |

The first task includes model initialization and is not comparable with later
task latencies. Across tasks 2–10, the observed mean was 1,000.5 ms and median
was 211.2 ms, but output lengths differ and no warm-up was performed.

## What the real run found

The numeric 0.800 must not be presented as semantic accuracy:

1. The keyword evaluator produces a false negative when a response says
   “red shape ... circle” instead of the contiguous phrase “red circle”.
2. `spatial-above-001` asks for object names but its references additionally
   require both colors.
3. `shapes-multi-001` labels a 60×60 generated square as a rectangle.

These are evaluation defects, not evidence of three model failures. The raw
score remains unchanged in this report so that the finding is auditable.

## Failures encountered and fixed

- The package index initially selected CPU-only PyTorch even though an NVIDIA
  GPU was present. `doctor --backend qwen3-vl` now detects this mismatch.
- Qwen3-VL processing required Torchvision, which was missing from the first
  optional dependency declaration. It is now included and checked.
- A stalled Hugging Face Xet transfer was replaced locally with resumable
  HTTP ranges. Both the PyTorch wheel and model weights were checked against
  their official SHA-256 values before use. This download workaround is not
  part of the repository runtime.

Typed adapter failures preserved the unsuccessful attempts as
`model_load_error` records instead of losing the run.

## Next action

Create `synthetic-v1.1` rather than silently changing released `synthetic-v1`:

- correct the square/rectangle reference;
- align the spatial prompt and reference strictness;
- add category-specific structured scoring so equivalent descriptions do not
  fail only because words are non-contiguous;
- then rerun Qwen3-VL with warm-up and three repetitions.

Peak VRAM, time to first token, throughput, and separated preprocessing/load
timings remain future measurements.

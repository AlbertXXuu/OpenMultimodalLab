# Qwen3-VL-2B vs SmolVLM2-500M: First Formal Comparison

Date: 2026-07-31

## Result

On the ten-task `synthetic-v1.1` set, Qwen3-VL-2B achieved a mean
deterministic score of `1.000`; SmolVLM2-500M achieved `0.733`. Both completed
all 30 measured attempts without runtime failures and produced identical
answers across all three repetitions of each task.

SmolVLM2 used substantially less peak allocated GPU memory—`1,265.3 MiB`
versus Qwen's `4,093.3 MiB`—but it was not faster on the median task. Its median
TTFT was `257.6 ms` versus `107.4 ms`, and its median end-to-end task latency
was `386.7 ms` versus `182.8 ms`.

The main explanation is visible in the raw input metadata. For the first task,
SmolVLM2's native image-splitting processor produced 13 visual tiles and 883
input token IDs; Qwen's native processor produced 102 input token IDs. A
smaller parameter count did not compensate for the larger native input
representation on these images.

This is a resource-efficiency comparison between a 2B and a 500M model, not a
same-size architecture comparison and not a claim about general multimodal
quality.

## Formal protocol

Both configurations used:

- the same clean Git commit: `e6d25410e66c483747a519b1877f0ae4a1d5b380`;
- the same `synthetic-v1.1` JSONL and byte-identical project-generated media;
- the exact stored prompts and fixed task order;
- deterministic decoding with `do_sample=false`, batch size 1, and
  `max_new_tokens=64`;
- one auditable warm-up attempt followed by three measured repetitions;
- the same Windows machine, Python 3.11 environment, CUDA runtime, and package
  versions;
- each model's pinned native processor and chat template.

The two finalized manifests independently record matching dataset/media
hashes, matching task IDs, `dirty=false`, and `status=completed`.

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
| Qwen checkpoint | `Qwen/Qwen3-VL-2B-Instruct` at `89644892e4d85e24eaac8bacfd4f463576704203` |
| Smol checkpoint | `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` at `7b375e1b73b11138ff12fe22c8f2822d8fe03467` |
| Effective dtype | BF16 for both models |

## Quality

| Model | Mean score | Median score | Successful attempts | Runtime failures |
|---|---:|---:|---:|---:|
| Qwen3-VL-2B | 1.000 | 1.000 | 30/30 | 0 |
| SmolVLM2-500M | 0.733 | 1.000 | 30/30 | 0 |

Category means:

| Category | Attempts/model | Qwen3-VL-2B | SmolVLM2-500M |
|---|---:|---:|---:|
| Image description | 6 | 1.000 | 0.500 |
| Spatial reasoning | 12 | 1.000 | 0.583 |
| Counting | 9 | 1.000 | 1.000 |
| Visual comparison | 3 | 1.000 | 1.000 |

SmolVLM2's three deterministic misses were attribute-completeness errors, not
inference failures:

| Task | Required information | Stable SmolVLM2 response | Score |
|---|---|---|---:|
| `spatial-above-001` | both colors, both shapes, relation | `Green is above orange.` | 0.333 |
| `shapes-multi-001` | three colors bound to three shapes | `Blue, Yellow, Green.` | 0.000 |
| `spatial-between-001` | color and shape | `Purple` | 0.000 |

The benchmark correctly distinguishes “the model answered” from “the answer
satisfied the declared task contract.” Both models had 100% runtime success,
but only Qwen had 100% deterministic task score.

## Performance

Warm-up is excluded from every aggregate below.

| Metric | Qwen3-VL-2B | SmolVLM2-500M |
|---|---:|---:|
| Median task latency | 182.8 ms | 386.7 ms |
| P95 task latency | 2,023.0 ms | 794.2 ms |
| Median preprocessing | 4.4 ms | 64.9 ms |
| Median TTFT | 107.4 ms | 257.6 ms |
| P95 TTFT | 120.9 ms | 264.5 ms |
| Median generation | 176.4 ms | 319.6 ms |
| Median generated IDs/s | 13.2 | 9.5 |
| Median decode IDs/s | 20.0 | 33.1 |
| Peak allocated GPU memory | 4,093.3 MiB | 1,265.3 MiB |
| Warm-up model load | 11,300.7 ms | 9,484.6 ms |

Interpretation:

- SmolVLM2 reduced peak allocated memory by about 69%, making it the more
  accessible backend for constrained devices.
- Qwen had about 2.4 times lower median TTFT and about 2.1 times lower median
  task latency on this task mix.
- SmolVLM2's lower P95 task latency does not prove better tail efficiency.
  Qwen generated much longer, fully attributed descriptions on the two
  description tasks: their median output length was 46 IDs for Qwen versus 12
  for SmolVLM2.
- Token throughput is not directly comparable across model families because
  their tokenizers encode text differently. It remains useful for repeated
  measurements within one model configuration.

Median category latency and output length show the output-length confound:

| Model/category | Median latency | Median output IDs |
|---|---:|---:|
| Qwen / image description | 1,549.0 ms | 46 |
| Smol / image description | 655.8 ms | 12 |
| Qwen / counting | 160.5 ms | 2 |
| Smol / counting | 379.0 ms | 3 |
| Qwen / spatial reasoning | 197.8 ms | 2.5 |
| Smol / spatial reasoning | 385.5 ms | 3 |

## Native preprocessing evidence

For `shapes-basic-001`:

| Field | Qwen3-VL-2B | SmolVLM2-500M |
|---|---|---|
| Input token IDs | 102 | 883 |
| Pixel tensor shape | `[320, 1536]` | `[1, 13, 3, 512, 512]` |
| Processor | `Qwen2VLImageProcessor` | `SmolVLMImageProcessor` |
| Native image behavior | patch/merge configuration | image splitting, max tile edge 512 |

The benchmark does not force one model's resizing policy onto the other. It
keeps semantic input pixels and prompt text constant, uses each pinned native
processor, and records the resulting representation.

## Reproduction

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-comparison-formal.jsonl

.\.venv-ml\Scripts\oml.exe run `
  --backend smolvlm2 `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/smolvlm2-500m-comparison-formal.jsonl
```

## Preserved evidence

| Artifact | SHA-256 |
|---|---|
| [Qwen raw JSONL](results/2026-07-31-qwen3-vl-comparison-formal.jsonl) | `BB3CD773A66B85713D221E632CE44D0D561950D6EDE4CE9C8BB0CCACFD7E10FF` |
| [Qwen manifest](results/2026-07-31-qwen3-vl-comparison-formal.manifest.json) | `FE4F4CE01102CF572A61AD11C102D332609D8A374D6420D11D3205F05FFE5B0A` |
| [Smol raw JSONL](results/2026-07-31-smolvlm2-500m-comparison-formal.jsonl) | `841002994BE8F733BAB0CC9CA4E5627B4E0198145A84871BD1B61427086625BA` |
| [Smol manifest](results/2026-07-31-smolvlm2-500m-comparison-formal.manifest.json) | `E367C63C7547FC398AB7C0A3196C17EFB699E56F0C57BA1BA12469A0B45E28A8` |

## Limitations

- Ten synthetic English image tasks are an integration benchmark, not a broad
  real-world capability benchmark.
- The models differ by approximately four times in parameter count.
- Deterministic scoring measures adherence to explicit answer contracts; it
  does not measure style, factuality outside the task, or human preference.
- `peak_gpu_memory_mb` is PyTorch maximum allocated memory during generation,
  not whole-system GPU usage.
- Model-load time includes local processor and weight initialization and should
  not be treated as a download benchmark.
- Transformers 5.14 emits a known top-level `pad_token_id` warning for the
  Smol checkpoint; its pinned generation config uses valid IDs and all 31
  attempts completed.

## Next decision

Do not add a third model yet. The next useful expansion is a licensed document,
OCR, table, and chart set with structured field scorers. The current synthetic
set already demonstrates the runner and model trade-off; broader task coverage
is now more valuable than another backend.

# SmolVLM2 Backend

SmolVLM2 is the second real model family supported by OpenMultimodalLab. It is
included to test whether the benchmark can compare independently developed
models through one execution and measurement contract, rather than to inflate
the backend count.

## Pinned checkpoint

The default checkpoint is
[`HuggingFaceTB/SmolVLM2-500M-Video-Instruct`](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct):

```text
revision = 7b375e1b73b11138ff12fe22c8f2822d8fe03467
license = Apache-2.0
```

The immutable revision is used for both the model and processor. Published
runs must not replace it with `main`.

## Why this model

SmolVLM2 was selected after reviewing SmolVLM2, Janus-Pro, and DeepSeek-VL2:

- it belongs to a different model family from Qwen3-VL;
- its model card and repository declare Apache-2.0;
- it has native Transformers image and video support;
- the 500M model card reports about 1.8 GB VRAM for video inference;
- its video capability can later reuse the same backend for the short-video
  part of the roadmap.

Janus-Pro remains useful for a later custom-runtime integration. It was not
selected for the first comparison because it adds a model-specific package,
remote custom code, and a separate model license at the same time. DeepSeek-VL2
is not a safe native-fit assumption for the current 8 GB GPU.

Selection does not prove runtime compatibility. Only the committed local
results and manifest establish whether this exact configuration completed.
The first comparison is intentionally a resource-efficiency trade-off between
Qwen3-VL-2B and SmolVLM2-500M, not a same-size architecture comparison.

## Installation

Use a separate Python 3.11 or 3.12 environment for real models:

```powershell
py -3.11 -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install --upgrade pip
.\.venv-ml\Scripts\python.exe -m pip install -e ".[smolvlm2]"
.\.venv-ml\Scripts\oml.exe doctor --backend smolvlm2
```

The first run downloads about 2 GB of pinned model files from Hugging Face.
Keep sufficient disk space and do not interrupt the initial download.
`doctor` reports model-cache disk availability and warns below 4 GiB free,
while keeping the cache path private. Existing cached weights may still run
below that recommendation, so the warning does not by itself fail readiness.

## Smoke run

Start with the three constrained counting tasks:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend smolvlm2 `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --category counting `
  --max-new-tokens 16 `
  --output runs/smolvlm2-counting-smoke.jsonl
```

Inspect both the summary and raw failures:

```powershell
.\.venv-ml\Scripts\oml.exe report `
  --input runs/smolvlm2-counting-smoke.jsonl

Get-Content runs/smolvlm2-counting-smoke.jsonl
```

## Formal run

Use the same tasks, prompt text, deterministic decoding, task order, token
limit, warm-up count, and repetitions as the Qwen3-VL baseline:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend smolvlm2 `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/smolvlm2-synthetic-v1.1-formal.jsonl
```

The adapter records the model and processor classes, native chat-template path,
model/processor revision, dtype, device, input tensor shapes, image-processor
settings, token counts, load/media/preprocessing times, synchronized TTFT,
generation time, throughput, and peak allocated CUDA memory.

## Comparison boundary

Both real backends receive the same RGB pixels and stored task prompt, then use
their own pinned native processor and chat template. Model-specific resizing
and tokenization are part of the model system being evaluated and are visible
through the immutable processor revision and raw usage metadata.

Token throughput must be interpreted cautiously across families because
tokenizers can split the same answer into different numbers of IDs. Quality,
end-to-end task latency, TTFT, failures, and peak memory are the primary
cross-family comparison fields; per-model token throughput remains useful for
repeated measurements of that model.

## Current limitations

- The adapter currently accepts still images only even though the model can
  process video. Video frame sampling and schema support must be specified
  before that path is enabled.
- It uses native, unquantized BF16 loading so the repository's FP32 storage
  dtype does not force CPU offload on the 8 GB target. Quantized runs would be
  a separate configuration and cannot be mixed into the native comparison.
- It does not claim broad real-world accuracy from the small synthetic set.
- A successful `doctor` checks packages and CUDA visibility, not model weights
  or available VRAM under load. It also requires CUDA BF16 support for the
  verified profile.
- Transformers 5.14 emits an upstream top-level `pad_token_id` validation
  warning while reading this checkpoint. The pinned generation config uses
  valid `pad_token_id=2` and `eos_token_id=49279`; the adapter does not silently
  rewrite upstream configuration. Treat actual generation failure, not the
  warning alone, as incompatibility.

## Primary sources

- [SmolVLM2-500M-Video-Instruct model card](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct)
- [Transformers SmolVLM documentation](https://huggingface.co/docs/transformers/model_doc/smolvlm)

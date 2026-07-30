# Qwen3-VL Backend

This is the first real vision-language model backend in OpenMultimodalLab.
It runs locally through Hugging Face Transformers and keeps the core `mock`
workflow dependency-free.

## Why this model

The default checkpoint is `Qwen/Qwen3-VL-2B-Instruct`:

- 2B parameters are realistic for an 8GB consumer GPU;
- the model and repository use Apache-2.0;
- Transformers supports its multimodal chat template directly;
- it covers image, spatial, document, and video understanding needed by the
  project roadmap;
- the 3.96GB weight file leaves some VRAM for vision inputs and generation.

The default immutable revision is:

```text
89644892e4d85e24eaac8bacfd4f463576704203
```

Published runs must keep this revision or explicitly record a replacement with
`--model-revision`.

## Windows GPU setup

Use a separate Python 3.11 or 3.12 environment. The CUDA wheel command is
specific to NVIDIA GPUs and should be selected from the official PyTorch
installer for the driver and platform in use.

The following configuration was selected for the initial Windows experiment:

```powershell
py -3.11 -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install --upgrade pip
.\.venv-ml\Scripts\python.exe -m pip install `
  torch==2.13.0 `
  torchvision==0.28.0 `
  --index-url https://download.pytorch.org/whl/cu130
.\.venv-ml\Scripts\python.exe -m pip install -e ".[qwen3-vl]"
```

Installing the project extras before the CUDA wheel can select a CPU-only
PyTorch package on some package indexes. `doctor` detects that mismatch:

```powershell
.\.venv-ml\Scripts\oml.exe doctor --backend qwen3-vl
```

Do not continue to a formal GPU run unless it reports that CUDA is available to
PyTorch.

## First run

Start with the single visual-comparison task:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --category visual-comparison `
  --max-new-tokens 32 `
  --output runs/qwen3-vl-single.jsonl
```

After that succeeds, run the ten-task image set with the formal timing profile:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-synthetic-v1.1-formal.jsonl
```

The first command downloads the pinned model into the Hugging Face user cache.
Weights and raw runs are intentionally excluded from Git.

## Recorded configuration

Every successful record includes:

- model and processor revision;
- backend name;
- device and dtype;
- deterministic `do_sample=false`;
- maximum generated tokens;
- input and output token counts.
- model loading, media loading, preprocessing, TTFT, generation, and text
  decoding time;
- generated-token and decode-only throughput;
- maximum allocated CUDA memory during generation.

Every CLI run also writes a portable manifest beside the JSONL output. The
manifest hashes the task file and media and records the effective environment,
Git state, repetitions, warm-up, model identity, and timing definitions.

Model-load errors and CUDA out-of-memory failures become explicit
`model_load_error` and `out_of_memory` records instead of terminating the run
without evidence.

## Current limits

- Only image media is validated by this first slice.
- The adapter uses batch size 1 and greedy decoding.
- TTFT marks completion of first-token logits inside local generation; it is
  not application streaming latency.
- Peak GPU memory is allocated memory, not the CUDA allocator's reserved pool
  or total system VRAM.
- A single successful run remains an engineering smoke test, not a publishable
  comparison.

## Primary references

- [Qwen3-VL-2B-Instruct model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)
- [Qwen3-VL official repository](https://github.com/QwenLM/Qwen3-VL)
- [Transformers multimodal chat templates](https://huggingface.co/docs/transformers/chat_templating_multimodal)
- [PyTorch local installation selector](https://docs.pytorch.org/get-started/locally/)

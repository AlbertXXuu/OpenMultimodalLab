# Reproducible short-video benchmark

This tutorial runs the canonical `synthetic-video-v1` tasks through the same
bounded local-video path used by the v1.0.0 candidate. The media, prompts,
expected answers, model revisions, and preserved results are all reviewable in
the repository.

![A factual comparison built from the committed formal results](../assets/video-benchmark-demo.gif)

The animation shows `video-right-end`, one of the 24 reviewed video tasks. In
formal repetition 1, Qwen3-VL-2B answered `right` and passed; SmolVLM2-500M
answered `left.` and failed. The same outcomes occurred in all three measured
repetitions. The GIF is generated from committed evidence—it does not rerun or
simulate either model.

## 1. Verify the runtime

Use the Python 3.11 model environment described in the
[backend guides](../backends/qwen3-vl.md):

```powershell
.\.venv-ml\Scripts\oml.exe doctor --backend qwen3-vl
.\.venv-ml\Scripts\oml.exe doctor --backend smolvlm2
```

Both commands must report a CUDA runtime, BF16 support, and ready status before
a real-model run.

## 2. Run a small video slice

The `motion-direction` category contains four tasks and is a useful first GPU
check:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-video-v1.jsonl `
  --media-root . `
  --category motion-direction `
  --max-new-tokens 32 `
  --output runs/video-motion-qwen.jsonl

.\.venv-ml\Scripts\oml.exe report `
  --input runs/video-motion-qwen.jsonl
```

This is a functional check, not a formal performance comparison.

## 3. Use the formal protocol

For a protocol-compliant comparison, use the same task set and generation
limit for both models, with exactly one warm-up and three complete measured
repetitions:

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-video-v1.jsonl `
  --media-root . `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/video-qwen-formal.jsonl

.\.venv-ml\Scripts\oml.exe run `
  --backend smolvlm2 `
  --dataset examples/tasks/synthetic-video-v1.jsonl `
  --media-root . `
  --warmup 1 `
  --repetitions 3 `
  --max-new-tokens 64 `
  --output runs/video-smolvlm2-formal.jsonl
```

The published v1.0.0 candidate instead used the single SHA-bound
`runs/formal-evaluation-input.jsonl`, which includes all 102 image, document,
video, and robustness tasks. Its raw evidence and manifests are retained under
`docs/reports/results/`.

## 4. Rebuild this demonstration

With PyAV and Pillow installed in `.venv-ml`, rebuild the GIF from the
committed video and formal JSONL:

```powershell
.\.venv-ml\Scripts\python.exe scripts/build_video_demo.py
```

The generator rejects a changed task/media reference, missing repetition,
non-success result, or unexpected pass/fail pattern before writing the GIF.
This makes the visual a traceable presentation layer over the raw evidence,
not a hand-authored model claim.

## 5. Interpret the result

This one task demonstrates temporal-position behavior, not general model
quality. The complete candidate report compares 102 tasks and shows the larger
trade-off: Qwen has the higher aggregate score and lower median latency, while
SmolVLM2 uses substantially less peak GPU memory. Always cite the
[complete report](../reports/v1.0.0-candidate/report.md) alongside a single
demo example.

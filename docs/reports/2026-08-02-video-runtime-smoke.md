# Shared short-video runtime smoke

Date: 2026-08-02

## Outcome

The pinned Qwen3-VL-2B-Instruct and SmolVLM2-500M-Video-Instruct backends both
completed a real local GPU inference from the same short MP4 through the new
shared video path. Each model answered that the red block moved to the right.

This closes the Adapter/runtime feasibility question; it does **not** complete
the video milestone. The clip was temporary, the run used one invocation per
model, and no versioned licensed video task set exists yet. These measurements
must not be presented as a formal benchmark or broad model comparison.

## Input and preprocessing

The smoke script generated a two-second, project-created MP4 outside the
repository:

- 160 × 120 RGB frames;
- 16 source frames at 8 FPS;
- one red block moving from left to right;
- no third-party image, video, or audio content.

Both backends received the same eight uniformly sampled frames. PyAV reported
the selected source indexes as `0, 2, 4, 6, 8, 10, 12, 14`. The Adapter passed
the decoded array and source metadata to each native processor and disabled
processor-side re-sampling. This avoids the Transformers 5.14 fallback to the
deprecated torchvision video reader on this Windows environment.

## Observed smoke results

Hardware: NVIDIA GeForce RTX 4060 Laptop GPU, 8,188 MiB, driver 596.49.
Runtime: Windows, Python 3.11, PyTorch 2.13.0+cu130, Transformers 5.14.1,
PyAV 18.0.0. Both model and processor revisions remained pinned.

| Backend | Response | Video input evidence | TTFT | Generation | Peak allocated VRAM |
|---|---|---|---:|---:|---:|
| Qwen3-VL-2B | `right` | `pixel_values_videos=[320,1536]`, `video_grid_thw=[1,3]` | 8,011.6 ms | 8,811.3 ms | 4,098.5 MiB |
| SmolVLM2-500M | `right.` | `pixel_values=[1,8,3,512,512]` | 12,057.3 ms | 16,988.3 ms | 1,177.3 MiB |

Model loading is excluded from TTFT and generation time. These first video
invocations can include cold CUDA/kernel effects and had no warm-up or repeated
measurements, so their latency values are diagnostic evidence only.

## Evidence retained by the implementation

Every successful video record now includes:

- media type and image/video counts;
- requested and actual video frame counts;
- source FPS, duration, dimensions, decoder, and sampled frame indexes;
- video decoding time as a subset of media-loading time;
- native image/video processor classes and serializable settings;
- effective input tensor shapes;
- TTFT, generation/decode throughput, and peak allocated CUDA memory.

When a selected task set contains video, its run manifest also records the
fixed `video_num_frames` configuration and hashes the original media file.
Invalid extensions, missing decoder support, malformed video, or empty decoded
frames become typed invalid-input evidence rather than an unexplained crash.

## Verification

- 90 offline tests passed in the Python 3.13 core environment.
- The same 90 tests passed in the Python 3.11 CUDA/model environment.
- Both `doctor --backend` checks passed with CUDA visible; SmolVLM2 also passed
  the BF16 capability gate.
- Both official processors decoded and tensorized the temporary clip.
- Both complete pinned models generated the expected direction on the 8 GB GPU.
- Repository checks covered 93 text files, 101 Markdown links, and 171
  JSON/JSONL documents with this report included.

## Remaining work

1. Confirm the public dataset name and any task-schema change before creating
   the committed video corpus.
2. Generate and manually inspect at least ten licensed short-video tasks that
   cover event order, motion direction, action, and scene change.
3. Complete warm-up plus three measured repetitions for both models and retain
   all failures and manifests.
4. Expand the complete human-checked corpus from 42 to at least 100 tasks.

Primary implementation references are the
[Transformers multimodal chat-template guide](https://huggingface.co/docs/transformers/main/chat_templating_multimodal),
[Qwen3-VL model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct), and
[SmolVLM2 model card](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct).

# Deterministic short-video corpus tooling

This tooling generated the approved `synthetic-video-v1` 24-task candidate.
Its dataset, eight clips, eight contact sheets, and SHA-bound review record are
committed. `AlbertXXuu` completed all 24 review entries on 2026-08-10, and the
record validates against the unchanged dataset hash.

## What is generated

The generator creates eight project-authored clips:

| Clip family | Assets | Questions |
|---|---:|---:|
| Horizontal/vertical motion | 4 | 12 |
| Appearance/disappearance order | 2 | 6 |
| Color state change | 1 | 3 |
| Count increase | 1 | 3 |
| **Total** | **8** | **24** |

Every clip has 16 frames at 8 FPS and 160×120 resolution. The file is a
deterministic, uncompressed 24-bit AVI written with the Python standard
library. It carries no encoder timestamp, host path, downloaded media, audio,
or third-party creative content. The same inputs therefore produce identical
bytes without depending on an installed FFmpeg encoder.

The companion contact sheet shows frames `0`, `5`, `10`, and `15` in
top-left, top-right, bottom-left, and bottom-right order. Runtime inference
uses frames `0, 2, 4, 6, 8, 10, 12, 14`; the human review record requires the
reviewer to confirm that the answer remains visible under that exact sample.

## Rebuild the approved candidate

Use a temporary directory while the public dataset name is unapproved:

```powershell
.\.venv\Scripts\python.exe scripts/generate_synthetic_videos.py `
  --output-dir examples\assets\synthetic-video-v1 `
  --review-dir docs\reviews\synthetic-video-v1 `
  --dataset-output examples\tasks\synthetic-video-v1.jsonl `
  --dataset-version synthetic-video-v1 `
  --media-prefix examples/assets/synthetic-video-v1 `
  --review-output docs\reviews\synthetic-video-v1.json
```

The script still has no inferred output name and refuses a partial dataset
configuration. Rebuilding the review template resets every human check to
`false`, so do not run this command over a completed review record.

## Human review protocol

For every task, a human reviewer must inspect the video/contact sheet and
approve all five statements:

1. the media opens and plays;
2. the answer is visible in the exact eight sampled frames;
3. the prompt and reference answer match the media;
4. the answer is unambiguous;
5. project-generated provenance and Apache-2.0 licensing are correct.

The reviewer then records a name, `YYYY-MM-DD` date, and optional notes. The
new template intentionally has every check set to `false`; generating it is
not evidence of review.

Validate the completed record with:

```powershell
.\.venv\Scripts\python.exe scripts/validate_human_review.py `
  --dataset "$draft/tasks.jsonl" `
  --review "$draft/review.json"
```

The validator requires exactly one entry for every task, the expected check
set, matching media references, the fixed sampling/contact-sheet order, and a
reviewer/date. It also binds the review to the exact dataset SHA-256, so any
later prompt, answer, metadata, ordering, or whitespace change invalidates the
old sign-off.

## Current implementation evidence

On 2026-08-02, the tooling was checked without committing a canonical draft:

- two independent generations produced byte-identical AVI and PNG files;
- all eight AVIs decoded as 16 frames, 160×120, and 8 FPS through PyAV;
- decoded-pixel checks confirmed the intended rightward and downward motion,
  excluding vertical inversion or RGB/BGR channel errors;
- the pinned Qwen3-VL-2B and SmolVLM2-500M backends both consumed the generated
  AVI through their full processors on the 8 GB RTX 4060 and answered the
  one-word rightward-motion diagnostic correctly;
- both records retained the exact eight sampled indexes; observed TTFT was
  842.9 ms for Qwen and 231.9 ms for Smol, with 4,096.2 MiB and 1,177.6 MiB
  peak allocated VRAM respectively.

This is one cold diagnostic invocation per model. It proves format/runtime
compatibility only and is not a formal quality or performance result.

## Remaining freeze and formal-run steps

Generation, hash binding, and owner review are complete. The remaining steps
are to freeze the reviewed bytes and run both pinned models with one warm-up
and exactly three repetitions.

Do not rename a canonical dataset after formal runs. A content change requires
a new version and new review hash.

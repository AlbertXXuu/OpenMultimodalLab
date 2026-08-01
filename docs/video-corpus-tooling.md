# Deterministic short-video corpus tooling

This tooling prepares a reviewable 24-task short-video draft without choosing
its public dataset name. It does not make the current 42-task canonical corpus
larger by itself. The dataset version, repository paths, generated media, and
completed review record must only be committed after the repository owner
approves the dataset name.

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

## Generate a non-canonical draft

Use a temporary directory while the public dataset name is unapproved:

```powershell
$draft = "runs/video-corpus-draft"

.\.venv\Scripts\python.exe scripts/generate_synthetic_videos.py `
  --output-dir "$draft/assets" `
  --review-dir "$draft/review-sheets" `
  --dataset-output "$draft/tasks.jsonl" `
  --dataset-version candidate-video-v0 `
  --media-prefix assets `
  --review-output "$draft/review.json"
```

`candidate-video-v0` is deliberately a temporary example, not an approved
public dataset name. The script has no canonical output default and refuses a
partial dataset configuration.

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

## Canonicalization after approval

After the owner approves a dataset version:

1. generate into `examples/assets/<approved-version>` and
   `examples/tasks/<approved-version>.jsonl`;
2. regenerate a fresh review template from those exact bytes;
3. inspect all eight clips and all 24 task/answer pairs;
4. complete and validate the review record;
5. add the approved dataset and review report to the release-readiness map;
6. run both pinned models with one warm-up and exactly three repetitions.

Do not rename a canonical dataset after formal runs. A content change requires
a new version and new review hash.

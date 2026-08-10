# Deterministic visual-robustness corpus tooling

This tooling generated the released `synthetic-robustness-v1` 36-task corpus.
Its dataset, 12 images, overview sheet, and SHA-bound review record
are committed. `AlbertXXuu` completed all 36 review entries on 2026-08-10, and
the record validates against the unchanged dataset hash.

## Coverage design

The generator creates 12 project-authored images and three independently
scored questions per image:

| Robustness factor | Images | Tasks | Intended stress |
|---|---:|---:|---|
| Small object | 3 | 9 | Detect a 12-14 pixel colored target on a 320x240 canvas |
| Low contrast | 3 | 9 | Separate a muted target from a related pale background |
| Visual clutter | 3 | 9 | Identify one colored target among neutral distractors |
| Partial occlusion | 3 | 9 | Recover color, shape, and occluder evidence |
| **Total** | **12** | **36** | Four controlled robustness slices |

Every image supplies color and shape questions. The third question measures
position, counting, or occlusion reasoning. This produces 36 unique task IDs,
24 attribute-recognition tasks, six spatial tasks, three counting tasks, and
three occlusion tasks. Thirty-two use normalized exact match and four use
zero-tolerance numeric scoring.

The PNG encoder, drawing primitives, scene values, prompts, and reference
answers are all stored in the repository. Assets have no encoder timestamps,
downloaded media, host paths, or third-party creative content, so independent
generations are byte-identical and licensed under Apache-2.0 with the project.

## Rebuild a disposable verification copy

Use a temporary directory so the completed review record and released assets
cannot be overwritten:

```powershell
$reviewBuild = Join-Path ([IO.Path]::GetTempPath()) `
  ("oml-robustness-review-" + [guid]::NewGuid())

.\.venv\Scripts\python.exe scripts/generate_robustness_images.py `
  --output-dir "$reviewBuild\assets" `
  --review-sheet "$reviewBuild\overview.png" `
  --dataset-output "$reviewBuild\tasks.jsonl" `
  --dataset-version synthetic-robustness-v1 `
  --media-prefix examples/assets/synthetic-robustness-v1 `
  --review-output "$reviewBuild\review.json"
```

The generator still has no inferred output name. It rejects an empty version,
partial dataset configuration, absolute media paths, Windows drive paths, and
parent-directory traversal. Rebuilding the review template resets every human
check to `false`, so do not run this command over a completed review record.
The logical media prefix remains canonical so the regenerated dataset bytes
can be compared with the released JSONL even though all output files are
written under the temporary directory.

## Review-sheet order

The full-resolution overview is ordered left to right, then top to bottom:

1. small red square, small blue circle, small green triangle;
2. low-contrast red circle, blue square, and green triangle;
3. cluttered purple triangle, orange circle, and green square;
4. occluded red circle, blue square, and green triangle.

The record binds that exact media order to the dataset. A reviewer should also
open individual PNGs at their original 320x240 resolution; the overview is a
navigational aid, not a substitute for per-task inspection.

## Human review protocol

For every task, a human reviewer must approve all five statements:

1. the media opens and renders at its intended resolution;
2. the declared robustness condition is visibly present;
3. the prompt and reference answer match the media;
4. the answer is unambiguous to a careful human;
5. project-generated provenance and Apache-2.0 licensing are correct.

The reviewer records a name, an exact `YYYY-MM-DD` date, and optional notes.
Every new template starts with all checks set to `false`; generation alone is
never evidence of human review.

Validate a completed record with:

```powershell
.\.venv\Scripts\python.exe scripts/validate_human_review.py `
  --dataset "$reviewBuild\tasks.jsonl" `
  --review "$reviewBuild\review.json"
```

The validator requires exactly one entry per task, the static-image check
profile, matching media references and review-sheet order, reviewer/date, and
the exact dataset SHA-256. Any prompt, answer, metadata, ordering, or whitespace
change invalidates the old sign-off.

## Current implementation evidence

On 2026-08-02, without committing a canonical draft:

- two independent generations produced byte-identical PNG and overview bytes;
- standard-library PNG decoding checks confirmed dimensions and target colors;
- pixel assertions confirmed small-object, muted-color, clutter-target, and
  target-behind-occluder semantics;
- a full-resolution visual inspection confirmed all four sheet rows rendered
  with the intended targets and stress conditions;
- both pinned real backends completed all 36 draft tasks on the 8 GB RTX 4060
  without a runtime failure; Qwen scored `0.889` with 4,089.7 MiB peak
  allocated VRAM and SmolVLM2 scored `0.861` with 1,265.7 MiB;
- per-factor inspection showed both models were perfect on the visual-clutter
  slice and made different errors on small-object, low-contrast, and occlusion
  tasks, providing a useful non-saturated diagnostic rather than duplicate
  easy questions;
- incomplete, reordered, stale-hash, unsafe-path, and unsupported review inputs
  were rejected by automated tests.

The model figures come from one cold pass with no warm-up and no repetitions.
They prove runtime compatibility and diagnostic value only; they are not
formal model-quality/performance results and do not increase the canonical
task count.

## Released status

Generation, hash binding, owner review, byte freeze, and inclusion in both
pinned-model formal runs are complete in v1.0.0.

Do not rename the canonical dataset after review or formal runs. A content
change requires a new version and a new review hash.

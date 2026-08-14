# Final-corpus human review

The approved video and robustness datasets were reviewed by `AlbertXXuu` on
2026-08-10. The image and document datasets received the same task-by-task,
SHA-bound review on 2026-08-14. Every check in all four JSON records is `true`;
each review applies only while its recorded dataset hash remains unchanged.

| Dataset | Tasks | Human-viewable media | Reviewed | SHA-bound record |
|---|---:|---|---|---|
| `synthetic-v1.1` | 10 | Ten full-resolution PNGs | 2026-08-14 | [`synthetic-v1.1.json`](synthetic-v1.1.json) |
| `synthetic-docs-v1` | 32 | Eight full-resolution document PNGs | 2026-08-14 | [`synthetic-docs-v1.json`](synthetic-docs-v1.json) |
| `synthetic-video-v1` | 24 | Eight AVI clips and eight four-frame contact sheets | 2026-08-10 | [`synthetic-video-v1.json`](synthetic-video-v1.json) |
| `synthetic-robustness-v1` | 36 | Twelve full-resolution PNGs and one overview sheet | 2026-08-10 | [`synthetic-robustness-v1.json`](synthetic-robustness-v1.json) |

The current dataset SHA-256 values are:

- `synthetic-v1.1`: `682e4089fc2f9793209b40beb0026279bd0f58d3ec4fcf75d3f65abba88e4692`
- `synthetic-docs-v1`: `79b9f2c25f2985b6ccbd6fba2e44d234685338534d3d810f4f2931eacdb9d610`
- `synthetic-video-v1`: `3d5c8449a1a63e7f115ba65a2d687c76fbe1aaf7021ad0d271581144966c7331`
- `synthetic-robustness-v1`: `e63e291e9bbaf62aa2521080a0e3c9e3ee8ec56a90df4ccd18b1624c5b25f757`

## Review protocol used

For all 24 video tasks, the reviewer opened the referenced AVI and matching PNG in
`docs/reviews/synthetic-video-v1/`. Confirm that the answer is visible in the
runtime sample at frames `0, 2, 4, 6, 8, 10, 12, 14`; the contact sheet shows
frames `0, 5, 10, 15` as an additional navigation aid.

For all 36 robustness tasks, the reviewer first used
`synthetic-robustness-v1-overview.png` for navigation, then inspected every
referenced image at its original 320x240 resolution.

For all 32 document tasks and all ten base image tasks, the reviewer used the
[image review workbook](image-review-workbook.md), opened every referenced PNG
at its original resolution, and compared every prompt and reference answer with
the visible evidence. The workbook is a viewing aid; the two JSON records are
the machine-validated evidence.

For every task, the reviewer compared the media with its prompt and expected
answer in the corresponding JSONL file and confirmed all five checks in the
JSON record. Each entry includes the reviewer name and ISO date.

Do not edit the JSONL datasets after review. Any byte change invalidates the
recorded SHA-256 and requires a new review.

## Validation

Every command must exit successfully. A later dataset edit or incomplete
review entry makes the corresponding validation fail:

```powershell
.\.venv\Scripts\python.exe scripts\validate_human_review.py `
  --dataset examples\tasks\synthetic-v1.1.jsonl `
  --review docs\reviews\synthetic-v1.1.json

.\.venv\Scripts\python.exe scripts\validate_human_review.py `
  --dataset examples\tasks\synthetic-docs-v1.jsonl `
  --review docs\reviews\synthetic-docs-v1.json

.\.venv\Scripts\python.exe scripts\validate_human_review.py `
  --dataset examples\tasks\synthetic-video-v1.jsonl `
  --review docs\reviews\synthetic-video-v1.json

.\.venv\Scripts\python.exe scripts\validate_human_review.py `
  --dataset examples\tasks\synthetic-robustness-v1.jsonl `
  --review docs\reviews\synthetic-robustness-v1.json
```

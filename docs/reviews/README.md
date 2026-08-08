# Final-corpus human review

The approved video and robustness datasets have been generated, but they are
**not yet human-approved**. Every check in both JSON records intentionally
starts as `false`; generated files are not evidence that a person reviewed
them.

| Dataset | Tasks | Human-viewable media | SHA-bound record |
|---|---:|---|---|
| `synthetic-video-v1` | 24 | Eight AVI clips and eight four-frame contact sheets | `synthetic-video-v1.json` |
| `synthetic-robustness-v1` | 36 | Twelve full-resolution PNGs and one overview sheet | `synthetic-robustness-v1.json` |

The current dataset SHA-256 values are:

- `synthetic-video-v1`: `3d5c8449a1a63e7f115ba65a2d687c76fbe1aaf7021ad0d271581144966c7331`
- `synthetic-robustness-v1`: `e63e291e9bbaf62aa2521080a0e3c9e3ee8ec56a90df4ccd18b1624c5b25f757`

## What the repository owner must inspect

For all 24 video tasks, open the referenced AVI and the matching PNG in
`docs/reviews/synthetic-video-v1/`. Confirm that the answer is visible in the
runtime sample at frames `0, 2, 4, 6, 8, 10, 12, 14`; the contact sheet shows
frames `0, 5, 10, 15` as an additional navigation aid.

For all 36 robustness tasks, first use
`synthetic-robustness-v1-overview.png` for navigation, then inspect every
referenced image at its original 320x240 resolution.

For every task, compare the media with its prompt and expected answer in the
corresponding JSONL file and confirm all five checks in the JSON record. A
review must also include the reviewer's name and an ISO date (`YYYY-MM-DD`).

Do not edit the JSONL datasets after review. Any byte change invalidates the
recorded SHA-256 and requires a new review.

## Validation

The following commands are expected to fail while the templates remain
incomplete. They must both exit successfully only after the owner has actually
performed and recorded the review:

```powershell
.\.venv\Scripts\python.exe scripts\validate_human_review.py `
  --dataset examples\tasks\synthetic-video-v1.jsonl `
  --review docs\reviews\synthetic-video-v1.json

.\.venv\Scripts\python.exe scripts\validate_human_review.py `
  --dataset examples\tasks\synthetic-robustness-v1.jsonl `
  --review docs\reviews\synthetic-robustness-v1.json
```

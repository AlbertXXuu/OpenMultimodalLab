# Final dependency and license audit

Outcome: PASS

Reviewer: Codex technical review (automated evidence; not legal advice)

Review date: 2026-08-10

Candidate commit: `3f2217f3299845ee4c10fe8c6b1236083fb30dc2`

Snapshot SHA-256: `aa2db1ca65a7bb1ac6e8ab4b0c7a1cdd069040c65175ffd043de3af60b1f9c33`

## Scope and command

The final audit was generated from the clean Windows Python 3.11 model
environment after installing OpenMultimodalLab 1.0.0:

```powershell
.\.venv-ml\Scripts\python.exe scripts\audit_runtime_licenses.py `
  --require-clean `
  --output docs\reports\results\final-runtime-license-audit.json `
  --constraints-output requirements\model-windows-py311-constraints.txt
```

The snapshot proves a clean source commit, 44 installed distributions, both
Apache-2.0 model cards at immutable revisions, 25 hashed PyAV binaries, and no
policy finding. The package inventory includes `openmultimodal-lab==1.0.0`.

| Artifact | SHA-256 |
|---|---|
| Runtime snapshot file | `baa8d03a418a6dca397b05d6767a0520032ceacde0416c6f3617d41567f1447e` |
| Exact Python constraints | `2f4caaf38b6ac6eaf2f49277b657d9691576f474a3ee1424a92041cd3b150e5f` |

The snapshot has its own canonical-content hash in addition to the ordinary
file hash shown above. The readiness checker recomputes that self-hash and
requires every constraints pin to match the snapshot inventory.

## Required distribution boundary

The project release is source-only. It must not include model weights, Python
wheels from the ML environment, CUDA libraries, PyAV/FFmpeg DLLs, or a bundled
executable.

PyAV 18.0.0 declares BSD-3-Clause, but its Windows wheel contains `libx264`,
`libx265`, and OpenCORE AMR components. Under the recorded FFmpeg policy, the
conservative effective binary classification is `GPL-3.0-or-later`. No
`libfdk` nonfree marker was found. This user-installed runtime is acceptable
for local execution; redistributing it would require a separate review.

The two retained warnings are therefore intentional evidence, not suppressed
failures:

1. never attach the PyAV/FFmpeg runtime binaries to the source release;
2. retain notice review for the weak-copyleft metadata reported for `certifi`,
   `num2words`, and `tqdm`.

No legal guarantee is claimed. The machine snapshot, policy, constraints, and
third-party notice are the reviewable engineering record.

# Public-release readiness

This records the evidence-backed gate that v1.0.0 passed and remains the
reusable minimum for future releases. It distinguishes implemented behavior,
verified evidence, future work, and decisions only the repository owner can
authorize.

Run the informational audit at any time:

```powershell
.\.venv\Scripts\python.exe scripts/check_release_readiness.py
```

The final release gate is strict and must exit `0`:

```powershell
.\.venv\Scripts\python.exe scripts/check_release_readiness.py --strict
```

Strict mode passes for the owner-approved `v1.0.0` release. It must not be
weakened for future releases merely to make CI green.

The technical gate excludes only the repository-owner external release
decision:

```powershell
.\.venv\Scripts\python.exe scripts/check_release_readiness.py --technical-strict
```

The final release passes this technical gate. The repository became public and
the owner authorized the formal `v1.0.0` GitHub Release on 2026-08-10. Full
`--strict` therefore passes all 19 checks.

## Current evidence matrix

| Requirement | Current evidence | Status |
|---|---|---|
| Two real open model families on an 8 GB GPU | Qwen3-VL-2B and SmolVLM2-500M formal manifests on RTX 4060 Laptop 8,188 MiB | Proven |
| Image input and formal comparison | Same-commit 102-task, two-model raw JSONL and manifests include the image tasks | Proven |
| Document/table/chart input and formal comparison | Same final grid includes all 32 document tasks | Proven |
| Short-video runtime | Same final grid includes all 24 reviewed video tasks with bounded eight-frame decoding | Proven formally |
| Licensed versioned short-video tasks | 24 `synthetic-video-v1` tasks over eight project-generated AVI clips | Generated, SHA-bound, and owner-reviewed |
| Short-video corpus tooling | Byte-stable eight-clip/24-task generator plus SHA-bound human-review validator | Released and owner-reviewed |
| Visual-robustness corpus tooling | Byte-stable 12-image/36-task generator across four controlled factors plus SHA-bound review | Released and owner-reviewed |
| At least 100 unique, human-checked tasks | All 102 unique licensed tasks have task-by-task, date- and SHA-bound owner review records under `docs/reviews/` | Proven for the current corpus |
| Formal video metrics for both models | One warm-up plus three complete repetitions for both pinned models | Proven |
| Quality, TTFT, throughput, memory, and failures | Preserved for all 612 measured attempts; zero runtime failures | Proven for all 102 tasks |
| Rebuildable reports and visuals | Final raw JSONL/manifests plus deterministic Markdown/CSV/failure/SVG bundle and self-hashed manifest | Proven for the released 102-task corpus |
| English main README and Chinese guide | `README.md` and `README.zh-CN.md` | Proven |
| Tutorial/demo | First experiment tutorial plus a reproducible GIF and short-video benchmark tutorial | Proven; the demo discloses one preserved model failure |
| Tests and Linux CI | Python 3.11/3.12, wheel build, fresh install, outside-checkout smoke | Proven on final PR evidence commit |
| Final GitHub Linux CI | Three successful jobs on main run `31363336845` | Proven for merge commit `62536b0af804579593ed0bef1f02e2281a8ff0ef` |
| Local Python 3.11/3.13 | 155 tests passed in each environment; Python 3.11 includes PyAV decoding | Proven on the frozen v1.0 evidence commit |
| Fresh Windows environment | New Python 3.13 build and Python 3.11 install environments outside checkout | Proven for the 1.0.0 wheel |
| Security | Final Bandit and dependency-advisory evidence plus bounded-input/path-privacy controls | Proven with disclosed low/residual risks |
| Code/model/data licenses | Clean 44-package/25-binary snapshot, exact constraints, signed report, and source-only boundary | Proven; no runtime binary may be attached |
| Project/package/import/CLI/dataset/public version names | `docs/release-approvals.json` records the owner's 2026-08-09 approval | Proven |
| Repository visibility | Owner approved publication on 2026-08-10; GitHub and anonymous HTTP checks report the repository as public | Proven |
| Formal GitHub Release | Owner authorized `v1.0.0`; the tag and Release target the final green main commit | Proven |
| Adoption claims | README links only verified artifacts and a structured first-run feedback path | Proven truthful |

## Required final sequence

1. **Complete:** record explicit naming approval without changing repository visibility.
2. **Complete:** all 102 licensed tasks are generated and have validated,
   task-by-task, SHA-bound owner review records.
3. **Complete:** both pinned models ran the complete canonical corpus with one
   warm-up and three measurements, preserving every result and failure field.
4. **Complete:** the final deterministic report bundle was built from raw
   artifacts, passes self/source/output verification, and was independently
   rebuilt byte for byte.
5. **Complete:** the exact dependency/license inventory and constraints were
   regenerated from the final Python 3.11 model environment, including the
   PyAV wheel's bundled FFmpeg evidence.
6. **Complete:** Python 3.11/3.13, fresh Windows installation, GitHub Linux CI,
   repository audit, wheel smoke, security review, and technical strict
   readiness all pass with retained final reports.
7. **Complete:** project/package/CLI/dataset/public-version names are approved,
   and the repository is public.
8. **Complete:** the owner separately approved the formal `v1.0.0` GitHub
   Release, created from the final green main commit without bundled runtime or
   model binaries.

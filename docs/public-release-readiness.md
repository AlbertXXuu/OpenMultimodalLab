# Public-release readiness

This is the living, evidence-backed gate for a job-showcase-quality public
v1.0. It deliberately distinguishes implemented behavior, locally verified
evidence, remaining engineering work, and decisions that only the repository
owner can authorize.

Run the informational audit at any time:

```powershell
.\.venv\Scripts\python.exe scripts/check_release_readiness.py
```

The final release gate is strict and must exit `0`:

```powershell
.\.venv\Scripts\python.exe scripts/check_release_readiness.py --strict
```

Strict mode currently exits `1` by design. It must not be weakened merely to
make CI green.

The technical gate excludes only the repository-owner publication decision:

```powershell
.\.venv\Scripts\python.exe scripts/check_release_readiness.py --technical-strict
```

The final candidate passes this technical gate. Full `--strict` remains open
while the private-to-public transition and formal Release are unauthorized.

## Current evidence matrix

| Requirement | Current evidence | Status |
|---|---|---|
| Two real open model families on an 8 GB GPU | Qwen3-VL-2B and SmolVLM2-500M formal manifests on RTX 4060 Laptop 8,188 MiB | Proven |
| Image input and formal comparison | Same-commit 102-task, two-model raw JSONL and manifests include the image tasks | Proven |
| Document/table/chart input and formal comparison | Same final grid includes all 32 document tasks | Proven |
| Short-video runtime | Same final grid includes all 24 reviewed video tasks with bounded eight-frame decoding | Proven formally |
| Licensed versioned short-video tasks | 24 `synthetic-video-v1` tasks over eight project-generated AVI clips | Generated, SHA-bound, and owner-reviewed |
| Short-video corpus tooling | Byte-stable eight-clip/24-task generator plus SHA-bound human-review validator | Proven tooling and reviewed candidate |
| Visual-robustness corpus tooling | Byte-stable 12-image/36-task generator across four controlled factors plus SHA-bound review | Proven tooling and reviewed candidate |
| At least 100 unique, human-checked tasks | 102 unique licensed tasks: 42 covered by existing reports and 60 covered by validated owner-signed records | Proven for the current corpus |
| Formal video metrics for both models | One warm-up plus three complete repetitions for both pinned models | Proven |
| Quality, TTFT, throughput, memory, and failures | Preserved for all 612 measured attempts; zero runtime failures | Proven for all 102 tasks |
| Rebuildable reports and visuals | Final raw JSONL/manifests plus deterministic Markdown/CSV/failure/SVG bundle and self-hashed manifest | Proven for the 102-task candidate |
| English main README and Chinese guide | `README.md` and `README.zh-CN.md` | Proven |
| Tutorial/demo | First experiment tutorial plus a reproducible GIF and short-video benchmark tutorial | Proven; the demo discloses one preserved model failure |
| Tests and Linux CI | Python 3.11/3.12, wheel build, fresh install, outside-checkout smoke | Proven on final PR evidence commit |
| Final GitHub Linux CI | Three successful jobs on run `31334039731` | Proven for commit `6703de8df7abacbfc8d8e4fb461b3a0eaefe2237` |
| Local Python 3.11/3.13 | 155 tests passed in each environment; Python 3.11 includes PyAV decoding | Proven on the frozen candidate |
| Fresh Windows environment | New Python 3.13 build and Python 3.11 install environments outside checkout | Proven for the 1.0.0 wheel |
| Security | Final Bandit and dependency-advisory evidence plus bounded-input/path-privacy controls | Proven with disclosed low/residual risks |
| Code/model/data licenses | Clean 44-package/25-binary snapshot, exact constraints, signed report, and source-only boundary | Proven; no runtime binary may be attached |
| Project/package/import/CLI/dataset/public version names | `docs/release-approvals.json` records the owner's 2026-08-09 approval | Proven; publication remains separate |
| Repository visibility and formal Release | Current visibility is recorded separately from the unapproved target; repository remains private | Owner decision required |
| Star/user claims | README explicitly refuses fabricated adoption claims | Proven truthful |

## Required final sequence

1. **Complete:** record explicit naming approval without changing repository visibility.
2. **Complete:** 102 licensed tasks are generated and the 24 video plus 36
   robustness tasks have validated owner review records.
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
7. **Partly complete:** project/package/CLI/dataset/public-version names are
   approved. Public visibility and the formal Release remain separate owner
   decisions.
8. Only after approval, make the repository public and create the formal
   Release; do not infer approval from implementation progress.

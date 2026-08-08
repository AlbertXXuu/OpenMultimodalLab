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

## Current evidence matrix

| Requirement | Current evidence | Status |
|---|---|---|
| Two real open model families on an 8 GB GPU | Qwen3-VL-2B and SmolVLM2-500M formal manifests on RTX 4060 Laptop 8,188 MiB | Proven |
| Image input and formal comparison | Same-commit 10-task, two-model raw JSONL and manifests | Proven |
| Document/table/chart input and formal comparison | Same-commit 32-task, two-model raw JSONL and manifests | Proven |
| Short-video runtime | Both full models completed a bounded eight-frame diagnostic clip | Proven runtime only |
| Licensed versioned short-video tasks | No committed canonical video task set | Open; owner must confirm dataset name first |
| Short-video corpus tooling | Byte-stable eight-clip/24-task generator plus SHA-bound human-review validator | Proven tooling; generated draft is not canonical evidence |
| Visual-robustness corpus tooling | Byte-stable 12-image/36-task generator across four controlled factors plus SHA-bound review | Proven tooling; generated draft is not canonical evidence |
| At least 100 unique, human-checked tasks | 42 canonical tasks with review reports | Open; 58+ additional unique tasks required |
| Formal video metrics for both models | No warm-up plus three-repeat video task-set run | Open |
| Quality, TTFT, throughput, memory, and failures | Present in preserved image/document records | Proven for current formal slices |
| Rebuildable reports and visuals | Raw JSONL/manifests, strict formal-grid validation, deterministic Markdown/CSV/failure/SVG bundle, self-hashed build manifest, tamper tests | Proven tooling and current 42-task baseline; final corpus bundle open |
| English main README and Chinese guide | `README.md` and `README.zh-CN.md` | Proven |
| Tutorial/demo | Complete first experiment tutorial and result visuals | Proven for image/document; final video demo open |
| Tests and Linux CI | Python 3.11/3.12, wheel build, fresh install, outside-checkout smoke | Proven on merged private `main`; rerun after final corpus |
| Final GitHub Linux CI | No final-candidate CI evidence report | Open; rerun after the final corpus and wheel are frozen |
| Local Python 3.11/3.13 | Complete suites pass locally | Proven for current commit; rerun on final candidate |
| Fresh Windows environment | Prior wheel audit exists | Must be repeated on final candidate |
| Security | Bounded-input/path-privacy review plus automated regression tests | Proven for current scope; dependency residuals remain |
| Code/model/data licenses | Apache-2.0 project/models/media plus a machine-verifiable package/PyAV-FFmpeg policy and audit tool | Tooling proven; final clean snapshot, constraints, and signed report open |
| Project/package/import/CLI/dataset/public version names | `docs/release-approvals.json` records the owner's 2026-08-09 approval | Proven; publication remains separate |
| Repository visibility and formal Release | Current visibility is recorded separately from the unapproved target; repository remains private | Owner decision required |
| Star/user claims | README explicitly refuses fabricated adoption claims | Proven truthful |

## Required final sequence

1. **Complete:** record explicit naming approval without changing repository visibility.
2. Build and human-review enough licensed tasks to reach at least 100 unique
   canonical tasks, including short video.
3. Run both pinned models on the final video and complete canonical corpus with
   one warm-up and three measurements, preserving every failure.
4. Build the final deterministic report bundle from raw artifacts, rebuild it
   independently byte-for-byte, run its self/source/output verification, and
   update the evidence matrix.
5. Regenerate the exact dependency/license inventory and constraints from the
   final Python 3.11 model environment, audit the PyAV wheel's bundled FFmpeg,
   and retain `final-dependency-license-audit.md`.
6. Verify Python 3.11/3.13 locally, fresh Windows installation, GitHub Linux CI,
   repository audit, wheel smoke, security review, and strict readiness check;
   retain the three independent final validation reports required by the
   checker.
7. Ask the owner to approve the project/package/CLI/dataset/public-version
   names, public visibility, and formal Release as separate external actions.
8. Only after approval, make the repository public and create the formal
   Release; do not infer approval from implementation progress.

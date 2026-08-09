# Final security review

Outcome: PASS

Reviewer: Codex technical review

Review date: 2026-08-10

Candidate commit: `3f2217f3299845ee4c10fe8c6b1236083fb30dc2`

## Executive summary

No critical, high, or medium source finding was found in the final local CLI
scope. Bandit reported eight low-severity subprocess heuristics; each is a
fixed-argument local Git or NVIDIA diagnostic call with no shell and no
task-controlled executable or argument. The dependency advisory audit found
no known vulnerability among 41 auditable installed distributions and
explicitly skipped three non-PyPI/custom distributions.

This is a bounded technical assessment, not a claim that native model and
media runtimes are vulnerability-free.

## Evidence

The scans ran from a disposable Python 3.11 tool environment outside the
repository, while inspecting candidate source and `.venv-ml` packages:

```powershell
python -m bandit -r src scripts -f json `
  -o docs/reports/results/final-bandit-security-audit.json
python -m pip_audit --path .\.venv-ml\Lib\site-packages `
  --format json `
  --output docs/reports/results/final-runtime-vulnerability-audit.json
```

| Artifact | Result | SHA-256 |
|---|---|---|
| Bandit JSON | 8 low, 0 medium, 0 high | `75bdfdee8c12849a4a62638c67efa64a1a92008749867d729aed34bb7d0c6afb` |
| pip-audit JSON | 41 audited, 0 known vulnerabilities, 3 skipped | `7eeedbe6e9ad0d464d87a6c5abf3fd2908894686388251ce18237d01e202a082` |

Before the final scan, four internal `assert` statements were replaced with
explicit checks that remain active under optimized Python. The shared adapter
now validates loaded dependencies at
`src/openmultimodal_lab/adapters/transformers_image_text.py:120`; both video
decoding and generation use that guard, and SmolVLM2 reuses it.

## Low findings reviewed

The remaining Bandit categories are:

- `B404` (3): importing `subprocess` in the CLI, manifest, and license tool;
- `B603` (3): executing fixed argument arrays with `shell=False`;
- `B607` (2): resolving the local `git` command through `PATH`.

These commands do not interpolate a prompt, task ID, media path, or model
output. They use fixed argument lists, captured output, checked return codes
where required, and timeouts in runtime paths. A user who maliciously controls
the Python process or its executable search path is outside the documented
local threat model.

## Dependency-audit limits

`pip-audit` skipped:

- `openmultimodal-lab==1.0.0`, because it is the local unpublished project;
- `torch==2.13.0+cu130` and `torchvision==0.28.0+cu130`, because those custom
  CUDA builds were not found on the audit index.

The exact skipped versions remain in the license snapshot and constraints.
Native PyAV/FFmpeg parsing, GPU kernels, model files, advisory-database
coverage, and cooperative-only CUDA timeouts remain residual risks. Published
benchmarks use project-generated bounded media; unknown media should be
processed in a disposable environment.

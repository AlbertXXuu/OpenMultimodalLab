# Fresh-install audit — v1.0.0

Date: `2026-08-28`

## Scope

This audit treated the public `README.md` at tag `v1.0.0` as the only setup guide. It did not modify
the tag, source code or published evidence. The source revision was
`ad443bc73bbfd1a2bbb81aa1e83324dc8a98afff`, checked out in a detached, clean worktree.

Two disposable clones were created under the workspace's ignored `.workspace/audits/` directory:

- Windows: Python `3.11.0`, Windows build `26200`;
- WSL Ubuntu: Python `3.12.3`, Ubuntu's installed system packages.

The mock path does not evaluate model quality. It audits installation, CLI, dataset loading, durable
evidence and report reading.

## Outcome

| Path | Result | Evidence |
| --- | --- | --- |
| Windows README install with build-network access | pass | editable install and every documented mock command exited `0` |
| Windows mock run after installation | pass | 3/3 attempts succeeded; JSONL and manifest were generated |
| Windows strict offline fresh install | fail | fresh venv lacked the `wheel`/`bdist_wheel` build command |
| WSL Ubuntu fresh setup | setup blocked | `python3 -m venv` reported that `python3.12-venv` was not installed |
| Linux project behavior | not rerun | no Linux behavior claim is made from the blocked WSL setup |

The standard Windows quick start is functional and completed well inside the documented ten-minute
target. A fully offline fresh install is not currently supported by the README unless build tooling
is already available. The WSL result is a missing OS prerequisite, not a failing OML test.

## Windows execution record

| Step | Command | Exit | Elapsed | Result |
| --- | --- | ---: | ---: | --- |
| clone | `git clone --branch v1.0.0 --depth 1 ...` | 0 | 0.827 s | clean detached tag checkout |
| environment | `py -3.11 -m venv .venv` | 0 | 10.744 s | Python 3.11.0 venv |
| strict offline install | `PIP_NO_INDEX=1 ... pip install -e . --no-build-isolation` | 1 | not completed | `invalid command 'bdist_wheel'` |
| documented install | `.venv\\Scripts\\python.exe -m pip install -e .` | 0 | 8.934 s | build dependencies obtained; package 1.0.0 installed |
| readiness | `.venv\\Scripts\\oml.exe doctor` | 0 | 0.471 s | `Status: core runtime ready.` |
| mock run | `.venv\\Scripts\\oml.exe run --dataset examples/tasks/smoke.jsonl --output runs/smoke-001.jsonl` | 0 | 0.478 s | 3 records, 100% runtime success |
| report | `.venv\\Scripts\\oml.exe report --input runs/smoke-001.jsonl` | 0 | 0.172 s | deterministic summary printed |
| tests | `.venv\\Scripts\\python.exe -m unittest discover -s tests -q` | 0 | 9.772 s | 157 passed, 1 skipped |

Generated ignored artifacts:

- `runs/smoke-001.jsonl`: 2,332 bytes;
- `runs/smoke-001.jsonl.manifest.json`: 2,367 bytes.

The clone remained clean because `runs/` and `.venv/` are ignored. No model was downloaded and no
provider credential was requested. The audit did not instrument all outbound sockets, so it does
not use this observation as proof of network isolation.

## Linux attempt

WSL Ubuntu had Python `3.12.3` and Git `2.43.0`. The local tag clone completed at the same revision.
The next README-equivalent step failed before project installation because the distribution lacked
the `python3.12-venv` OS package and therefore `ensurepip`. Installing system packages was outside
this documentation-only audit. Existing release-time Linux CI remains documented in
[final-linux-ci-validation.md](../reports/final-linux-ci-validation.md), but it is historical CI
evidence rather than a fresh Linux run on 2026-08-28.

## Observed friction

### F1 — Fresh install is network-dependent unless build tooling is preseeded

The runtime core has no mandatory third-party dependency, but a new venv still needs a sufficiently
new `setuptools` and `wheel` to build the editable package. Build isolation obtains these from the
configured package index. With index access disabled and build isolation disabled, metadata
generation failed at `bdist_wheel`.

Impact: the public quick start works in the usual networked setup, while “offline core” currently
describes runtime behavior after installation rather than a completely offline fresh install.

### F2 — Minimal Ubuntu needs an OS venv package

`python3 -m venv .venv` is not sufficient on a minimal Ubuntu installation without
`python3.x-venv`. The interpreter's error is actionable, but the README does not state this OS-level
prerequisite.

Impact: a new Linux user can stop before OML installation despite having a supported Python version.

### F3 — The Linux copy block names Python 3.11 only

The README states support for Python 3.11–3.13 in the core, while its Linux block uses
`python3.11` literally. A machine with only Python 3.12 must substitute `python3` or `python3.12`.

Impact: minor copy/paste friction; not a compatibility failure.

### F4 — Report output is terminal-only in the quick start

The `report` command prints the summary and does not create a separate Markdown artifact in this
path. The durable outputs are the run JSONL and manifest. A first user expecting a report file may
not know which artifact to retain.

Impact: evidence expectation is less explicit than the command behavior.

### F5 — Local shallow-clone warning

The local-source shallow clone printed `refs/tags/v1.0.0 ... is not a commit!` before successfully
checking out and identifying the annotated tag. This was observed with a local repository source and
is not evidence that the published GitHub clone emits the same warning.

Impact: none on this run; retained to avoid suppressing an observed warning.

## Recommended next actions

1. A004 should make the post-install contributor smoke path explicit and offline, without claiming
   that Python build-tool installation itself is offline.
2. A later documentation fix can state the build-network prerequisite, the Ubuntu venv package and
   the two durable quick-start artifacts. It should be a focused onboarding correction, not a new
   packaging abstraction.
3. Do not modify or recreate `v1.0.0`; apply any clarification to `main` and future releases.

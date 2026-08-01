# Fresh wheel installation audit

Date: 2026-08-01

Scope: dependency-free core, packaged wheel, and offline `mock` smoke path

Outcome: passed

## Why this audit exists

Editable installs can hide packaging defects because Python can import source
directly from the checkout. This audit tests the artifact a user would
actually install. The environment is created outside the repository, receives
only the built wheel, and runs the public CLI from its own `site-packages`.

## Windows evidence

The audit used a new Python 3.11 virtual environment under a unique temporary
directory. It did not reuse `.venv` or `.venv-ml`.

| Check | Observed result |
|---|---|
| Wheel build | `openmultimodal_lab-0.1.0-py3-none-any.whl` built successfully |
| Wheel install | Installed with `pip install --no-deps` |
| Import origin | Temporary environment `Lib/site-packages`, not the checkout |
| `oml doctor` | Core runtime ready |
| Offline run | 3/3 successful records |
| Scored smoke tasks | Mean score 1.000 on 2 deterministic checks |
| Report rebuild | Completed from the written JSONL |
| Dependency integrity | `pip check` reported no broken requirements |

The machine was Windows 11 with Python 3.11.0. An NVIDIA GPU was detected, but
the audit deliberately used `mock`; GPU availability therefore did not affect
the result. The output and manifest stayed in the temporary audit directory.

## Reproduction shape

The exact temporary path can differ. The important boundaries are shown below:

```powershell
python -m pip wheel . --no-deps --wheel-dir <wheelhouse>
py -3.11 -m venv <fresh-venv>
<fresh-python> -m pip install --no-deps <built-wheel>

Push-Location <directory-outside-checkout>
<fresh-oml> doctor
<fresh-oml> run `
  --dataset <checkout>\examples\tasks\smoke.jsonl `
  --media-root <checkout> `
  --output <temporary-output>\smoke.jsonl
<fresh-oml> report --input <temporary-output>\smoke.jsonl
<fresh-python> -m pip check
Pop-Location
```

## Permanent Linux gate

The repository-quality CI job now repeats the artifact boundary on Ubuntu with
Python 3.12:

1. build the wheel;
2. create a new virtual environment under the runner temporary directory;
3. install only that wheel;
4. run `doctor`, `run`, and `report` outside the checkout;
5. assert that `openmultimodal_lab` imports outside the workspace;
6. run `pip check`.

This turns a one-time local result into a regression gate for every pull
request and every push to `main`.

## Interpretation and limits

This proves that the core package metadata, console entry point, task loading,
runner, manifest, JSONL output, and report command work from a clean wheel
installation. It does not prove that optional real-model dependencies install
on every GPU platform, that model repositories remain available, or that the
small smoke set measures model quality. Those concerns retain separate backend
diagnostics, pinned revisions, contract tests, and formal local experiments.

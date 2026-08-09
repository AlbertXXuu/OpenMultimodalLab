# Final fresh Windows validation

Outcome: PASS

Validation date: 2026-08-10

Candidate commit: `3f2217f3299845ee4c10fe8c6b1236083fb30dc2`

Fresh environment: two newly created virtual environments outside the Git
checkout—Python 3.13.5 for the build and Python 3.11.0 for installation and
execution.

Wheel SHA-256: `463d679593239b14a8b6a7c5684c8b6b83a44bb7c1b53ee7b8690931d6c80d64`

Outside-checkout smoke: PASS

## Isolation procedure

1. Created a detached Git worktree at exactly the candidate commit and
   confirmed a clean detached `HEAD`.
2. Created a new Python 3.13 build environment outside the repository.
3. Built `openmultimodal_lab-1.0.0-py3-none-any.whl` (59,080 bytes) from that
   detached candidate.
4. Created a separate new Python 3.11 environment and installed only that
   wheel with `--no-deps`.
5. Changed to a directory outside both checkouts before exercising the CLI.

The installed package reported both distribution and module version `1.0.0`.
Its import path resolved inside the fresh environment's `site-packages`, not
the repository or candidate worktree.

## Checks and observed results

| Check | Result |
|---|---|
| `python -m pip check` | PASS; no broken requirements |
| `oml --version` | `oml 1.0.0` |
| `oml doctor` | PASS; core runtime ready on Windows, Python 3.11.0 |
| Installed import location | PASS; outside checkout |
| Offline smoke run | PASS; 3/3 successful, 2 scored, mean score 1.000 |
| Smoke report | PASS; reproduced the run summary |
| Candidate test suite using installed wheel | PASS; 155 run, 155 passed, 1 optional PyAV test skipped |

The PyAV skip is expected because the source-only core wheel deliberately has
no required third-party dependencies. The dedicated Python 3.11 model
environment ran the same PyAV decode test successfully during final local
validation.

The temporary environments contained no durable project evidence; this report
retains the candidate commit, wheel identity, commands, versions, and outcomes
needed to repeat the check.

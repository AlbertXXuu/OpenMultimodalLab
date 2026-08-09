# Final candidate validation

Outcome: PASS

Validation date: 2026-08-10

Candidate commit: `3f2217f3299845ee4c10fe8c6b1236083fb30dc2`

Python 3.11: PASS

Python 3.13: PASS

Repository audit: PASS

Wheel verification: PASS

Report rebuild: PASS

Security review: PASS

## Verification matrix

| Area | Evidence |
|---|---|
| Python 3.11 model environment | 155 tests passed in 11.324 s, including real PyAV decoding; `pip check` passed |
| Python 3.13 core environment | 155 tests passed in 12.570 s; one optional PyAV test skipped; `pip check` passed |
| Compilation | `compileall` passed for `src`, `scripts`, and `tests` |
| Repository audit | 149 text files, 148 Markdown links, and 1,053 JSON/JSONL documents passed UTF-8, link, secret, path, and structure checks |
| Formal input | 102 tasks verified at SHA-256 `d18e6dce941cfac1fee0d637449229d786d7d6b601c063c0af2266b7e2d7a5a8` |
| Final report | Both formal sources verified; an independent empty-directory rebuild produced all six files byte-for-byte identical to the committed bundle |
| Video demonstration | 16-frame GIF rebuilt with SHA-256 `d2840d7683dfb70ed31449846f325b6e0436529ba7322b8e5712c3b27e36a889`, identical to the committed artifact |
| Runtime licenses | 44 packages and 25 PyAV binaries; 0 policy findings; exact 43-pin constraints match the clean snapshot |
| Source security | Bandit: 8 reviewed low subprocess heuristics, 0 medium/high; all four removable `assert` findings fixed |
| Runtime advisories | 41 distributions audited with 0 known vulnerabilities; local project and two custom CUDA packages explicitly skipped and disclosed |
| Fresh Windows wheel | 59,080-byte wheel installed and executed outside checkout; 155 tests and 3-task smoke passed |

## Scope boundary

The formal 102-task, two-model GPU runs were already frozen on clean commit
`aeb445086001215dfe6f0c7fe04e6a7872f447c7`; their raw JSONL, manifests, input
and report hashes are protected by tests. This final candidate validation did
not rerun or replace that evidence.

GitHub Linux CI is intentionally recorded in a separate report after the
candidate evidence branch is pushed. Repository visibility and the formal
GitHub Release remain separate owner decisions and are not implied by this
technical PASS.

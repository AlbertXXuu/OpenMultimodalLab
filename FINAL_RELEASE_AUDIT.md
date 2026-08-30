# OpenMultimodalLab v1.1.0 final release audit

- Status: **PASS**
- Audit date: `2026-08-30` (`Asia/Shanghai`)
- Audited source commit: `dc4bb67b2c348113440c8d6bfbe9c1edc63ebe91`
- First complete Linux-CI candidate commit: `b77c46c2d0fdc6202a15f293e584c375de179b48`
- Target release: `v1.1.0`

## Release meaning

`v1.1.0` is the presentation and maintenance closure release built on the unchanged `v1.0.0`
research/evidence baseline. It adds the Studio, shared AlvenX production branding, documentation,
portability, responsive/accessibility work, and explicit version identity. It does not add a model,
benchmark, experiment, or research conclusion.

## Environment and method

The source commit was cloned into a separate local directory and audited without an editable install
from the development checkout. Windows validation used Windows NT `10.0.26200.0`, PowerShell
`7.6.4`, Python `3.11.0`, and Chromium `151.0.7922.34`. Built distributions were installed in two
new isolated environments, one from the wheel and one from the source distribution.

Linux is not inferred from the Windows result. The complete candidate passed the repository's
GitHub Actions matrix on Ubuntu. This record remains valid only while every check on the current
head of pull request [#55](https://github.com/AlbertXXuu/OpenMultimodalLab/pull/55) is green.

## Readiness checklist

| Surface | Result | Evidence |
| --- | --- | --- |
| Separate fresh clone | PASS | Clone HEAD exactly matched `dc4bb67b2c348113440c8d6bfbe9c1edc63ebe91`; worktree was clean before ignored build output. |
| Package/runtime identity | PASS | Project metadata, import metadata, `oml --version`, Studio, README files, and changelog identify software `1.1.0`; frozen reports remain evidence `v1.0.0`. |
| Source distribution | PASS | Built and installed in a new environment; metadata and CLI both reported `1.1.0`. |
| Wheel | PASS | Built and installed with no dependencies in a new environment; `pip check`, CLI identity, doctor, mock run, and report path passed outside the development checkout. |
| Windows/local tests | PASS | `201` unittest tests ran, `3` skipped; offline contributor smoke passed `3/3` tasks with its socket guard active. |
| Repository checker | PASS | `194` text files, `275` Markdown links, and `1,056` JSON/JSONL documents validated, including this audit record. |
| Committed evidence/report check | PASS | Rebuilt report verifier matched `4` sources and `5` outputs; runtime-license policy validation passed. |
| Linux CI | PASS | [Run 33314875863](https://github.com/AlbertXXuu/OpenMultimodalLab/actions/runs/33314875863) passed test on Python 3.11/3.12, repository quality, installed-wheel smoke, and Studio UI on the complete candidate. |
| README / README.zh-CN | PASS | Both are present, coherent with the `1.1.0` candidate identity, and retain the stable `v1.0.0` reproduction path. |
| CHANGELOG / MAINTENANCE | PASS | `CHANGELOG.md` and `docs/MAINTENANCE.md` are present and describe a bounded closure release plus maintenance-only follow-up. |
| PORTFOLIO | PASS | Problem, original decisions, difficult failure modes, results, negative/limited evidence, and individual contribution are recorded. |
| LICENSE / SECURITY / CITATION | PASS | `LICENSE`, `NOTICE`, `SECURITY.md`, and `CITATION.cff` are present; package licensing policy passed. |
| Studio | PASS | Run, Reports, and Method remained reachable; generation controls start collapsed; the compact result surface states score, latency, TTFT, peak VRAM, and `Unscored` when applicable. |
| Responsive/accessibility | PASS | Chromium at 900/1024/1280/1440/1600 px found no page overflow; critical targets are at least 44 px, keyboard focus is visible, and the shared header geometry/styles match. |
| Version labels | PASS | `Studio v1.1.0` and `Evidence v1.0.0` are deliberately separate. |
| Evidence and documentation links | PASS | Repository-local links passed the checker; dated README/portfolio external links returned HTTP 200. |
| Historical v1 integrity | PASS | Annotated tag, peeled commit, two formal-result blobs, and committed report-bundle tree match the closure baseline below. |
| Website links | PASS with publication sequencing | `https://alvenx.com` and repository links return HTTP 200; the local production website candidate's project route and repository links passed its P9 browser audit and are deployed in P11. |
| OG/social | PASS | GitHub exposes the custom 1280×640 repository image; fetched SHA-256 `f44b868678f4b64a598666fd4f383f7025d2bcec3a7b0aa2334bef093e49f7c0`. |

## Distribution artifacts

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `openmultimodal_lab-1.1.0-py3-none-any.whl` | 181,312 | `b5f2d46d42c1525d8a871e06c4d311165ac4aba56d478febb90c92431caaf060` |
| `openmultimodal_lab-1.1.0.tar.gz` | 226,855 | `7ec83ad3d3174d2a9a01191d60bcf0762d2b5c5476d0430bb3e24dce4b75c59b` |

Archive inspection confirmed Python source, CLI entry point, LICENSE/NOTICE, and packaged Studio
brand/font assets. The installed wheel's offline mock run produced three successful records and its
report reported 100% infrastructure-path success; that mock score is not a model-quality claim.

## Frozen v1.0.0 anchors

| Anchor | Expected and observed object ID |
| --- | --- |
| Annotated `refs/tags/v1.0.0` | `d3bfe1575fc6fb990a712bab6bad303ed148a700` |
| Peeled v1.0.0 commit | `ad443bc73bbfd1a2bbb81aa1e83324dc8a98afff` |
| Qwen formal-result blob | `a8efae91510ba0413e524d7d23edc374f36d0a11` |
| SmolVLM formal-result blob | `7b3b8f12125e20cf243fad1ea9c197ac4daad639` |
| v1.0.0 candidate report tree | `3108f7cebcec94f4d75c88d63fa8377dcbbd9986` |

All expected IDs equal the objects reachable from the audited candidate. No historical ref or
frozen evidence object changed.

## Findings and disposition

- **P0 blockers:** `0`.
- **P1 blockers:** `0`.
- **P2 accepted:** setuptools warns that the legacy TOML license table and license classifiers are
  deprecated, with a stated deadline of `2027-02-18`. The sdist and wheel build and install
  correctly. Migrating requires raising the build-system floor from setuptools 68 and changing
  package metadata; this is maintenance work, not a release blocker, and is intentionally not
  expanded inside closure.

## Gate decision

Release readiness is **PASS** with P0/P1 counts of zero. The audit-status reconciliation changes
only this document and must pass the same pull-request checks before merge. No tag or release may
be created until P11 validates the merged commit and reconfirms its current-head CI.

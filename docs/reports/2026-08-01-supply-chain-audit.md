# Dependency and supply-chain audit

Date: 2026-08-01

Outcome: no model weights, private run artifacts, or oversized tracked files
were found; two mutable GitHub Action references were fixed, and the first
grouped update was independently reviewed and passed CI.

## Reviewed scope

- all 92 files tracked before this audit;
- Git ignore and line-ending policy;
- GitHub Actions references and workflow permissions;
- Python core and optional dependency declarations;
- installed-license inventory in `THIRD_PARTY_NOTICES.md`;
- model checkpoint identifiers and immutable revisions;
- generated dataset license metadata;
- private vulnerability reporting availability for the current repository.

## Findings and actions

| Severity | Finding | Action |
|---|---|---|
| Medium | CI used mutable major tags for `actions/checkout` and `actions/setup-python`. | Replaced each tag with a full official commit SHA and retained an adjacent release comment for update tooling. |
| Low | Dependency updates depended on manual review. | Added grouped weekly Dependabot checks for `pip` and GitHub Actions, capped at two open version-update PRs per ecosystem. |
| Informational | Private vulnerability reporting is a feature for public repositories, while this repository is still private. | Kept the portable `SECURITY.md` fallback; enable GitHub private vulnerability reporting only after the owner approves public visibility. |

The repository checker now rejects any future remote workflow action that is
not pinned to a full 40-character commit SHA. Local actions and `docker://`
references are excluded from that rule because their integrity boundary is
different.

## Evidence

- `git ls-files` reported 92 tracked files before the audit.
- No tracked file exceeded 1 MiB.
- `.gitignore` excludes raw runs, environments, model/checkpoint directories,
  common model-weight extensions, secrets files, and build outputs.
- Core runtime dependencies remain empty; real-model dependencies are optional.
- Both default model repositories use immutable 40-character revisions.
- The committed synthetic task records declare Apache-2.0 and are regenerated
  byte for byte in tests.
- CI retains least-privilege `contents: read` workflow permissions.

## Pin sources

The commit identifiers were resolved from the official GitHub tag references
on the audit date:

| Action | Pinned commit | Human-readable tag |
|---|---|---|
| `actions/checkout` | `3d3c42e5aac5ba805825da76410c181273ba90b1` | `v7.0.1` |
| `actions/setup-python` | `5fda3b95a4ea91299a34e894583c3862153e4b97` | `v7.0.0` |

Dependabot understands both commit-pinned GitHub Actions and an adjacent tag
comment, so updates can retain immutable execution while still proposing new
upstream versions for review.

## First update validation

After the configuration reached `main`, Dependabot opened
[PR #14](https://github.com/AlbertXXuu/OpenMultimodalLab/pull/14) with a grouped
major update for both Actions. Before merging, the proposed SHAs were resolved
independently through the official GitHub tag API, the four-line workflow diff
and upstream release notes were reviewed, and Python 3.11, Python 3.12, and
repository-quality CI all passed. The PR was then merged manually. This is the
intended maintenance loop; Dependabot proposes evidence, but does not make the
acceptance decision.

## Residual risks

- Optional ML dependencies use compatible lower bounds, not a cross-platform
  lock file; formal runs must continue to preserve their resolved inventory.
- Model files are downloaded from upstream at runtime. Immutable revisions
  prevent tag movement but do not replace independent artifact attestation.
- The standard-library secret check covers common credential formats but is
  not a complete secret scanner or malware detector.
- Dependency updates must pass tests and be reviewed; they are not auto-merged.
- GitHub private vulnerability reporting remains a public-release action and
  cannot be enabled meaningfully while the repository is private.

Update on 2026-08-10: after the owner authorized public visibility, GitHub
private vulnerability reporting, Dependabot security updates, Secret Scanning,
and push protection were enabled for the public repository. The portable
`SECURITY.md` reporting path remains available.

# Dependency and supply-chain audit

Date: 2026-08-01

Outcome: no model weights, private run artifacts, or oversized tracked files
were found; two mutable GitHub Action references were identified and fixed.

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
| Medium | CI used mutable major tags for `actions/checkout` and `actions/setup-python`. | Replaced each tag with the full commit SHA currently resolved by the official `v6` tag and retained `# v6` for update tooling. |
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
| `actions/checkout` | `d23441a48e516b6c34aea4fa41551a30e30af803` | `v6` |
| `actions/setup-python` | `ece7cb06caefa5fff74198d8649806c4678c61a1` | `v6` |

Dependabot understands both commit-pinned GitHub Actions and an adjacent tag
comment, so updates can retain immutable execution while still proposing new
upstream versions for review.

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

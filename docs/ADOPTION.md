# Adoption ledger

- Snapshot date: `2026-08-28`
- Maintainer: `AlbertXXuu`
- Review cadence: monthly, on the 28th
- Next review: `2026-09-28`

This ledger tracks independently verifiable use of OpenMultimodalLab. It is a
measurement record, not a marketing counter. Unknown evidence stays unknown and
an empty category stays at zero.

## Current counts

| Evidence category | Count | Qualification rule | Current evidence |
| --- | ---: | --- | --- |
| Independent core installs | 0 | A non-author completes the documented core quick start in their own environment and provides the outcome or artifact. | No qualifying public or owner-provided record. |
| Independent third-party adapters | 0 | A non-author publishes or submits a runnable adapter with a pinned revision and contract evidence. | No qualifying public or owner-provided record. |
| Substantive external Issues or PRs | 0 | A non-author reports reproducible technical friction, supplies a useful design analysis, or proposes a focused patch. | The public Issue list is empty; all human-authored PRs are by the maintainer. |
| Independent benchmark reproductions | 0 | A non-author reruns a pinned benchmark and verifies the resulting records or report against the documented protocol. | No qualifying public or owner-provided record. |

The public snapshot was checked through the repository's
[`Issues`](https://github.com/AlbertXXuu/OpenMultimodalLab/issues?q=is%3Aissue)
and [`pull requests`](https://github.com/AlbertXXuu/OpenMultimodalLab/pulls?q=is%3Apr)
on `2026-08-28`. Dependabot activity, maintainer-authored PRs, CI runs and the
maintainer's own fresh-install audits do not qualify as independent adoption.

## Counting rules

1. **Independent** means the evidence producer is not the repository owner,
   automation acting for the repository, or a person executing a maintainer-run
   test session. Compensation or close project involvement must be disclosed.
2. **One person, one workflow, one version** counts once in a category. Repeated
   attempts update the outcome and friction notes rather than inflating the
   count. A person may qualify in two categories only by producing two distinct
   artifacts, such as a quick-start report and a new adapter.
3. A failed install is retained as first-use friction but does not count as a
   completed install. Silence or an unverified claim is `no evidence`, not a
   failure or rejection.
4. An adapter idea without runnable code and a bug report without reproduction,
   diagnostic evidence or a concrete design consequence do not qualify.
5. A benchmark reproduction must identify the project version, task or dataset
   version, backend revision, environment and result artifact. Reusing the
   maintainer's committed result is not a reproduction.
6. GitHub Stars, followers, page views, clones, forks and release-download totals
   are not adoption evidence. They cannot establish who ran the project or what
   outcome occurred.

## Privacy rules

- Prefer a public Issue, PR or repository URL as evidence.
- For privately supplied evidence, obtain permission to retain it and assign a
  pseudonymous evidence ID. Publish only the minimum aggregate fact unless the
  contributor separately consents to attribution.
- Do not retain credentials, private media, email addresses, IP addresses,
  machine names or absolute local paths in this ledger. A public username may
  remain visible through its source URL but is not copied into the entry.
- Redact logs before linking them. A request to remove private evidence changes
  the entry to `withdrawn`; it does not leave personal details in history.

## Entry schema and history

Each future entry must record:

| Field | Required content |
| --- | --- |
| `evidence_id` | Stable local ID such as `OML-ADOPT-0001`. |
| `observed_date` | ISO date when the outcome was observed. |
| `category` | Exactly one category from the current-count table. |
| `project_version` | Tag or immutable commit used by the participant. |
| `environment` | Bounded OS and Python/runtime facts needed to interpret the outcome. |
| `attempt` | The documented workflow, adapter or benchmark actually attempted. |
| `outcome` | Success, failure or partial result, including concrete friction. |
| `evidence` | Public URL or consented private evidence ID. |
| `counted` | `yes` or `no`, with the applicable rule. |

There are no qualifying entries in the history as of the snapshot date. New
entries are appended; corrections retain the original evidence ID and state the
reason for the change. At each monthly review, recheck links, recalculate the
four counts from qualifying entries, record withdrawn evidence, and set the next
review date.

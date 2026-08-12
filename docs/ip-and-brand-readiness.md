# IP and brand readiness

This document records the project's current intellectual-property posture and
the decisions still required before making stronger public claims. It is an
engineering checklist, not legal advice.

## Current position

- Project code and project-generated synthetic media are distributed under
  Apache-2.0. That license permits commercial use, modification, and
  redistribution when its conditions are met; it is not a non-commercial
  license.
- Apache-2.0 does not grant a general license to use the licensor's trade names
  or trademarks, except for reasonable customary use describing the origin of
  the work and reproducing a NOTICE file.
- The repository history, immutable `v1.0.0` tag, and published GitHub Release
  provide useful provenance, but provenance alone does not create a registered
  trademark or patent. The tag itself is not cryptographically signed, so the
  project must not describe it as a signed release artifact.
- `Ailumetra` is currently a public project brand. This repository does not
  claim that it is a registered trademark and must not display the registered
  symbol (`®`) unless registration actually exists in the relevant territory.

## Decisions that require the owner

Before adding a project-level copyright attribution or trademark ownership
statement, confirm the exact public identity and the scope of the claim. A
GitHub username, developer identity, natural-person name, and company name are
not interchangeable legal choices. Package author metadata is descriptive; it
does not determine legal ownership, and future contributors retain rights in
their contributions unless a separate agreement changes that result.

After that decision, the smallest coherent repository change is:

1. add a top-level `NOTICE` with the chosen copyright attribution;
2. add a short `TRADEMARKS.md` describing permitted descriptive references and
   prohibiting claims of endorsement or official status;
3. add the same ownership statement to both README license sections;
4. update package author/maintainer metadata only if it should identify the
   same public person or entity;
5. add `CITATION.cff` with the citation name the owner wants researchers to
   use.

Adding a copyright banner to every source file is not the first priority. It
creates a large blame-only diff and does not replace the repository-level
license and attribution decision.

## Trademark path

1. Search the exact word, visually similar words, and relevant goods/services
   in official trademark databases. A normal web search is only a preliminary
   collision check.
2. Decide who will own the application before filing.
3. Select exact goods and services based on what the project actually offers.
   Downloadable software commonly points toward Nice Class 9; hosted software,
   software development, or technical services commonly point toward Class 42.
   The classes alone are not a substitute for choosing defensible item wording.
4. File first in the territory where protection matters now; evaluate Madrid,
   US, or EU coverage only when users or commercial activity justify it.
5. Keep dated specimens showing genuine public use of the name and wordmark.

The owner should use a qualified trademark professional for a clearance opinion
before spending on filing or promotion at scale.

## Patent warning

Do not treat public Git history as a substitute for a patent strategy. Public
disclosure can become prior art and may destroy novelty outside narrow statutory
exceptions. The repository is already public, so any serious patent question
requires prompt advice from a patent professional based on the actual disclosure
dates and target countries. Do not publish a new technical method merely to
"protect it" before receiving that advice.

## What to preserve now

- immutable release tags and committed evidence hashes;
- original design/source files for the wordmark and social preview;
- dated benchmark records, build manifests, and human-review records;
- model and dependency license evidence;
- public posts and screenshots showing first use of the Ailumetra name;
- contributor authorship through normal Git commits and pull requests.

## Pending owner confirmation

- public copyright/trademark owner identity;
- whether to use the unregistered `™` indicator;
- filing territory and budget;
- exact Nice goods/services wording;
- whether author metadata should expose a legal name, a company, or a stable
  public developer identity.

## Authoritative references

Checked on 2026-08-12:

- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- [Apache guidance for applying the license](https://www.apache.org/legal/apply-license)
- [GitHub social-preview requirements](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
- [CNIPA trademark fee guide](https://sbj.cnipa.gov.cn/sbj/sbsq/sqzn/201912/t20191227_611.html)
- [CNIPA trademark application guide](https://www.cnipa.gov.cn/module/download/down.jsp?colID=2488&i_ID=155734)
- [CNIPA explanation of patent novelty exceptions](https://www.cnipa.gov.cn/jact/front/mailpubdetail.do?sysid=6&transactId=480300)
- [WIPO Global Brand Database](https://www.wipo.int/en/web/global-brand-database)

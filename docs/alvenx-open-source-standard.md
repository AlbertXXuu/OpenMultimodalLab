# AlvenX Open-Source Project Standard

**Standard:** AOS-0.1<br>
**Effective date:** 2026-08-15<br>
**Maintainer:** AlbertXXuu

## 1. Purpose and status

This document is the engineering and public-delivery contract for projects in
the AlvenX open-source series. It exists to make separate repositories feel
related without forcing them into one codebase or one research scope.

It is a maintainer-owned project standard, not an external certification, a
legal entity, or a claim that AlvenX is a registered trademark. A repository
may be technically complete while external adoption remains unvalidated; the
standard keeps those states separate.

The current series contains:

| Project | Primary research object | Current role |
|---|---|---|
| OpenMultimodalLab | Model capability under fixed tasks and inference conditions | Released evaluation infrastructure |
| Browser Agent Regression | Agent-system reliability under controlled browser changes | Time-boxed Phase 0 validation |

This file is the canonical copy of AOS-0.1. Each repository keeps a short
conformance record rather than duplicating the whole standard.

## 2. Identity hierarchy

The identity order is fixed:

1. **Functional project name** — primary repository, package, CLI, and README
   heading.
2. **Functional description** — the concrete developer job the project does.
3. **AlvenX** — the secondary series identity and shared quality story.

Therefore:

- the shared wordmark may appear at the top of a README;
- the wordmark signal line must describe the project domain;
- the README H1 must use the functional project name;
- repository, distribution, import, and CLI names remain function-led;
- `AlvenX` must not replace a clear product name or imply that a company,
  hosted service, or certification program already exists.

The standard does not require every project to use `Lab`, nor does it require
an `alvenx-` package prefix. Shared identity is not a reason to create a
shared runtime dependency.

## 3. Research and scope separation

The projects answer different questions:

```text
OpenMultimodalLab
same tasks + controlled inference protocol + different models
                         ↓
        quality / latency / memory / failures

Browser Agent Regression
same tasks + controlled environment + baseline/candidate agent system
                         ↓
       success / checkpoints / robustness / regression
```

For reliability work, an agent system may be reasoned about as:

```text
agent system = model + harness + tools + environment
```

That decomposition is a research frame, not an instruction to build a
universal harness benchmark. Browser Agent Regression begins with one browser
environment and one evidence-producing integration. A generic run identity or
adapter boundary is introduced only after repeated, real integration needs
make the abstraction necessary.

OpenMultimodalLab does not absorb harness, tool-use, memory, or agent-loop
evaluation. Browser Agent Regression does not duplicate model quality, VRAM,
or inference-throughput benchmarking. Brand consistency never overrides this
scope boundary.

## 4. README public contract

The first screen of every public AlvenX repository follows this order:

1. shared AlvenX wordmark with a project-specific signal line;
2. functional project-name H1;
3. one bold sentence connecting the project to AlvenX;
4. truthful CI, runtime, and license badges;
5. English/Chinese language switch when both documents are maintained;
6. one practical question or developer job;
7. current status with date or release/phase identifier;
8. the strongest directly inspectable evidence.

The README must also provide:

- a copyable quick start that has been executed from a clean environment;
- a boundary or limitations statement near the evidence it qualifies;
- links to raw evidence, not only screenshots or summary tables;
- contribution and security routes;
- no claims that depend on private results or future functionality.

## 5. Evidence contract

Every public experiment must preserve enough information to distinguish what
was measured from what is inferred. The exact file format may differ by
project, but the evidence must include:

- schema or evidence-contract version;
- evidence kind, including `synthetic`, `calibration`, or `real-agent` labels;
- UTC creation time;
- task/dataset identity and content hashes where practical;
- model, agent, harness, prompt, tool, and environment identity when each is a
  variable in the experiment;
- runtime and relevant hardware/software environment;
- complete configuration and repetition count;
- successes, failures, and the first diagnosable failure boundary;
- raw attempt-level records or a durable pointer to them.

Rules:

- failures are not silently removed from denominators;
- synthetic controls are never presented as real model or agent performance;
- a report or chart is derived evidence, not automatically the source of
  truth;
- a clean source state is preferred, but an artifact must not claim a Git
  revision it cannot truthfully bind;
- cherry-picked examples may illustrate a known result but cannot establish a
  general performance claim;
- public artifacts are scanned for credentials, usernames, private media,
  cookies, and absolute local paths.

## 6. Repository baseline

Before public user validation, a repository must have:

- English README and, when promised, maintained Chinese README;
- OSI-compatible project license and third-party notices required by included
  code, data, fonts, or media;
- `CONTRIBUTING.md` and `SECURITY.md`;
- reproducible environment metadata and a package/build manifest;
- automated lint or repository checks plus targeted tests;
- LF-normalized text and ignored local environments/build outputs;
- one installable, end-to-end path that exercises the claimed core value;
- a conformance record naming incomplete gates.

Issue templates, release automation, dashboards, and hosted demos are added
only when the current validation or release workflow needs them.

## 7. Verification and release levels

### Level E0 — Experiment slice

- the smallest end-to-end hypothesis is executable;
- deterministic controls pass their written gate;
- negative controls demonstrate that failure detection works;
- evidence and limitations are committed together.

### Level E1 — Public validation

- a fresh clone follows the README successfully;
- remote CI passes on the advertised primary platform;
- evidence links resolve from the public repository;
- security, licensing, and privacy checks pass;
- the repository clearly says which user-demand gates remain open.

### Level R1 — Formal release

- version, changelog, release notes, and immutable tag agree;
- release evidence binds the relevant source, inputs, and environment;
- supported installation paths have fresh verification;
- no known release-blocking correctness, security, licensing, or data-integrity
  issue remains;
- the owner explicitly approves the external release action.

External adoption is tracked separately at every level. Stars, page views, and
the maintainer's own runs do not count as independent use.

## 8. Claims and language

Public copy distinguishes:

- **fact:** directly supported by a linked artifact;
- **inference:** an interpretation bounded to the measured conditions;
- **hypothesis:** a claim the current phase is designed to test;
- **unknown:** adoption, generalization, or safety not yet measured.

Terms such as “best,” “state of the art,” “production-ready,” “universal,” and
“official” require evidence matching their scope. Third-party projects must not
be described as official because they target or support an official model.

## 9. Update cadence

The planning target is two or three meaningful public updates per week, not a
commit quota. Useful updates fall into at least one category:

- an engineering change with a verified user-visible outcome;
- a reproducible experiment with evidence;
- a documented failure, limitation, or decision;
- external-user feedback converted into an issue or fix.

Empty version bumps, cosmetic churn, generated commit noise, and speculative
architecture do not satisfy the cadence.

## 10. Conformance and evolution

Each project records items as `pass`, `partial`, `pending`, or `not applicable`
in `docs/alvenx-conformance.md`. A project may remain in the series with
pending items when the README states them accurately.

Changes to this standard require:

1. a concrete inconsistency, failure, or new release requirement;
2. a focused diff to this canonical file;
3. conformance review for every active series repository;
4. no new shared package or service unless real duplication across projects
   justifies it.

Brand-asset changes additionally require light/dark rendering review. Research
scope changes require a new project decision, not merely a standards edit.

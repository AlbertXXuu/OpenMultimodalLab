# Maintenance policy

Current public release: `v1.1.0`
Research/evidence baseline: immutable `v1.0.0`
Development mode: maintenance; no new research claim

## Frozen release surface

The `v1.0.0` tag and GitHub Release are immutable. The following release identities and claims are
not modified in place:

- the 102 reviewed task identities, media and dataset hashes;
- the two pinned model revisions and formal run configuration;
- raw JSONL results, run manifests and the byte-rebuildable report bundle;
- task/run schema versions, evaluation protocol and report-generator hash bound by the release;
- published measurements, failures, audits and stated limitations.

Corrections that affect interpretation are appended as dated errata or new evidence. They do not
rewrite the released bundle.

## Accepted maintenance

- correctness, security, portability, CI and dependency-compatibility fixes;
- documentation clarification and reproduction fixes;
- contributor onboarding that exercises the existing contract;
- narrowly scoped integrations supported by a concrete user request or research question.

Any behavior change needs tests. Commands presented as supported must be executed on the stated
platform; Windows and Linux claims require evidence from both.

## Expansion gate

A new adapter, task family, schema, UI surface, dependency or benchmark expansion must cite a
reproducible Issue, experiment failure, user need or registered hypothesis. It also needs an exact
model/data revision, license boundary, maintenance cost and an evaluation question not already
answered by v1. General completeness or model count is not sufficient evidence.

Follow-up research uses a new experiment ID and separate artifacts. If it changes a frozen contract,
it requires a new version rather than altering `v1.0.0`.

## Stop and escalation

Reject or pause work when it changes released evidence, lacks reproducible inputs, weakens failure
preservation, introduces unclear data rights, or adds maintenance cost without new information.
Security issues may justify a patch release; compatibility-breaking proposals require an explicit
decision log and release plan.

The detailed post-v1 rationale remains in [post-v1-roadmap.md](post-v1-roadmap.md).

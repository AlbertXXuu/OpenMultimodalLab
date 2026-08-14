# Post-v1 maintenance roadmap

OpenMultimodalLab v1.0.0 established a reproducible baseline: two pinned local
vision-language models, 102 licensed and human-reviewed multimodal tasks, a
fixed measurement protocol, and byte-verifiable evidence. Post-v1 work should
make that baseline easier to trust, reproduce, and extend—not inflate model or
commit counts.

The [human-review index](reviews/README.md) binds all 102 task-level approvals
to the exact four dataset hashes. These post-release records clarify the
review trail without moving or replacing the published `v1.0.0` tag.

## Why this remains useful

- It evaluates model choice on an accessible 8 GB GPU instead of assuming a
  datacenter environment.
- It preserves failures and hardware/task limitations instead of publishing a
  context-free leaderboard.
- It treats image, document, and short-video evidence through one versioned
  task and report contract.
- It provides license-clear, reproducible assets that contributors can inspect
  without downloading a hidden benchmark.

These are design properties, not claims of popularity or universal model
quality. User adoption and feedback are reported only when directly observed.

## Entry criteria for new work

A proposed feature or experiment enters `Now` only when it has:

1. a concrete user or research question;
2. a path reproducible on the documented hardware, or an explicit new hardware
   boundary;
3. immutable upstream revisions and license evidence;
4. the same task, scoring, and measurement contract for compared models;
5. a user-visible result, regression test, or preserved experiment artifact.

An adapter that only makes another model import successfully is not enough.

## Work tracks

### Now: reliability and first-use quality

- Reject malformed/non-finite JSON and incomplete run records at every public
  persistence boundary.
- Keep the English and Chinese entry points, tutorials, and release state in
  sync with tested commands.
- Repeat clean-install and report-rebuild checks after meaningful changes.
- Keep the v1.0 report generator byte-stable because release manifests bind
  its source hash. A future generator revision must use a new evidence bundle
  contract/version rather than rewriting released hashes.

### Next: evidence-led extension

- Run observed fresh-clone sessions with non-author users and fix the highest
  friction points.
- Publish an adapter template only after its contract tests and license/revision
  checklist are complete.
- Add one low-VRAM comparison at a time, each motivated by a question the
  existing v1.0 evidence cannot answer.

### Later: conditional scope

- Quantized or alternative runtimes when they enable a measured hardware or
  latency use case.
- Additional task families when their media can be regenerated and reviewed.
- A UI or remote execution layer only when CLI user evidence shows it removes a
  real barrier without weakening provenance.

## Maintenance targets, not achievements

The next validation targets are:

- five successful clean-environment runs by people other than the author;
- three substantive external Issues, Discussions, or pull requests that change
  a documented decision;
- a core quick start completed within 10 minutes, excluding model downloads;
- two or three substantive updates per week when evidence is ready.

Until measured, these remain targets. Empty commits, retrospective releases,
or invented feedback do not satisfy them.

## Stop conditions

Pause or reject work when it requires unclear data rights, cannot preserve raw
failures, changes a published dataset in place, lacks a reproducible hardware
path, or adds maintenance cost without answering a distinct question. Public
dataset, package, CLI, project, and release-version names still require owner
approval before they change.

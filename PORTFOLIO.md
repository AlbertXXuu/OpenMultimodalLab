# OpenMultimodalLab portfolio evidence

## Problem

Model demos and aggregate leaderboards do not answer which pinned vision-language model is suitable
for a specific local workload and hardware budget, or whether the conclusion can be rebuilt from
preserved evidence. OpenMultimodalLab provides versioned tasks, interchangeable adapters, durable
raw outputs, deterministic scoring and environment-aware reports.

## Why it was difficult

The result had to remain comparable across model families while preserving failures, media/task
identity, model revision, retries, interruptions and hardware timing. Inference and reporting also
had to stay separable so reports could be rebuilt without another model run.

## Project-specific decisions

- Keep raw JSONL and manifests authoritative; charts and summaries are derived artifacts.
- Use task-selected deterministic scoring instead of an LLM judge for the frozen corpus.
- Pin model revisions and hash task/media inputs.
- Separate warm-up from three measured repetitions and retain failed/slow attempts.
- Make resume verify the exact durable prefix instead of silently appending to incompatible output.

The rationale and limits are documented in [the evaluation protocol](docs/evaluation-protocol.md),
[artifact contract](docs/run-records-and-manifests.md) and
[risk/decision record](docs/08-risks-and-decisions.md).

## Most demanding engineering failure mode

Interrupted formal runs could otherwise be resumed against changed tasks, media, model settings,
environment or partial output. The strict resume path binds those identities, validates the exact
attempt prefix and checkpoints output atomically. Its failure-injection evidence is recorded in
[the resumable-run report](docs/reports/2026-07-31-resumable-runs.md).

## Verified result

On the recorded RTX 4060 Laptop GPU and frozen 102-task grid, Qwen3-VL-2B scored `0.784` with
`212.9 ms` median task latency and `4,180.5 MiB` peak allocated GPU memory; SmolVLM2-500M scored
`0.690`, `471.5 ms`, and `1,265.3 MiB`. Both completed 306 measured attempts with zero runtime
failures. See the [v1 report](docs/reports/v1.0.0-candidate/report.md).

## Negative evidence and limits

The result is not a universal ranking: it covers two revisions, one hardware profile and a reviewed
synthetic workload. Cross-family token throughput is not treated as equivalent. External adoption
and generalization beyond this grid are not established.

## External use

As of `2026-08-28`, this repository contains no qualifying record of an unfamiliar developer using
the tool for their own workflow. The next evidence target is an independent pinned-v1 quick start
with a report or concrete setup friction.

## Personal contribution

The repository history shows AlbertXXuu as the sole human code contributor. The owner is responsible
for problem framing, protocol and schema decisions, implementation acceptance, human task review,
local model experiments, evidence boundaries and release approval. Automated assistance does not
replace the owner's responsibility to explain and defend those decisions.

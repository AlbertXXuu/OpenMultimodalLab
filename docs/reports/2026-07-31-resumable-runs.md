# Strict Resumable Runs and Output Integrity

Date: 2026-07-31

## Result

OpenMultimodalLab can now recover a compatible interrupted run without
duplicating completed attempts or silently mixing experiments.

The safety contract is:

- a new CLI run refuses an existing output or manifest by default;
- `--overwrite` is required to replace them intentionally;
- `--resume` accepts only `started` or `failed` runs;
- every existing record must be the exact ordered prefix of the requested
  warm-up and measurement plan;
- dataset, media, task order, backend, model revision, generation settings,
  environment, packages, GPU, and Git state must match;
- output byte length, SHA-256, JSONL boundary, record count, and record
  identities must match before any append;
- every new record is flushed and synced before an atomic manifest checkpoint.

The final implementation passed all 59 tests in both the Python 3.13 core
environment and the Python 3.11 CUDA/ML environment.

## Why strict prefix recovery

Skipping by task ID alone is insufficient. One task can appear in a warm-up
and several measured repetitions, and its result depends on the model
revision, prompt, media, environment, and generation settings. A task-ID-only
resume can therefore create a complete-looking file whose rows came from
different experiments.

The runner instead derives one deterministic attempt plan:

```text
warm-up 1 / first task
measurement 1 / task 1
measurement 1 / task 2
...
measurement N / final task
```

The stored JSONL must match a prefix of this sequence. Resume begins at the
first missing attempt.

## Crash consistency

For each attempt, the runner:

1. finishes generation and scoring;
2. writes one complete JSONL line;
3. flushes the Python stream;
4. calls `fsync` on the output file;
5. atomically replaces the manifest with current counts, byte length, and
   SHA-256.

The file persistence and manifest update happen after the recorded
model-task latency is calculated, so they do not inflate inference latency.

There is an unavoidable two-file crash window between steps 4 and 5. A hard
stop in that window leaves an output newer than its last manifest checkpoint.
Resume rejects the size/hash mismatch instead of guessing or truncating.

## Failure-injection coverage

| Scenario | Expected behavior | Automated result |
|---|---|---|
| Adapter interrupted after one task | Preserve row and append only missing attempts | Passed |
| Existing output path reused normally | Exit 2; preserve bytes | Passed |
| `--resume` used on completed run | Reject; require a new output path | Passed |
| Output changed after failed run | Reject size/hash mismatch before generation | Passed |
| JSONL final newline removed | Reject incomplete durable boundary | Passed |
| Task order changed | Reject non-prefix record | Passed |
| Manifest count differs from JSONL | Reject count mismatch | Passed |
| Every row persisted | `fsync` occurs before checkpoint callback | Passed |

## User-visible smoke

The mock CLI smoke produced three successful records. Its completed manifest
reported the same byte size as the JSONL and the stored SHA-256 matched a
separate `Get-FileHash` calculation. A second invocation without
`--resume` or `--overwrite` exited with code 2 and left the output hash
unchanged.

Reproduction:

```powershell
.\.venv\Scripts\oml.exe run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/resume-safety-smoke.jsonl

.\.venv\Scripts\oml.exe run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/resume-safety-smoke.jsonl
```

The second command is expected to refuse replacement. To recover a genuinely
interrupted compatible run, repeat its original arguments and add
`--resume`.

## Scope and limitations

- Resume is intentionally sequential. Future parallel execution will require
  stable attempt IDs and a set-based recovery plan.
- A hash is not a signature. It detects an output change while the manifest is
  trusted, not a malicious rewrite of both artifacts.
- A hard stop between output sync and manifest replacement requires manual
  inspection; the tool does not silently discard the extra row.
- Per-attempt timeout and bounded retry remain separate work because they
  change failure semantics and should not be hidden inside resume.

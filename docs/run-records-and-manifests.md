# Run Records and Manifests

OpenMultimodalLab keeps two complementary artifacts:

- JSONL run records contain one durable result for every generation invocation;
- one JSON run manifest describes the complete experiment configuration and
  input identity.

The reporter reads JSONL only. A damaged or missing chart can therefore be
rebuilt without rerunning the model.

## Run record versions

| Version | Meaning |
|---|---|
| `0.1` | Initial task output, status, keyword score, and end-to-end latency |
| `0.2` | Task/dataset versions plus explicit metric identity and details |
| `0.3` | Warm-up/measurement phase and measured repetition |
| `0.4` | Durable retry chains, cooperative deadlines, and cumulative latency |

The reporter treats records without `phase` or `repetition` as one measured
legacy repetition. Existing result files remain readable. Resume remains
schema-strict: an interrupted 0.3 run must be finished with its original code
revision or restarted at a new output path; 0.3 and 0.4 rows are never mixed.

## Invocation and retry state

Schema 0.4 distinguishes a scheduled task measurement from the generation
invocations used to finish it:

| Field | Meaning |
|---|---|
| `attempt_index` | One-based invocation number inside this task/repetition |
| `terminal` | Whether this record completes the scheduled task attempt |
| `retryable` | Whether the status belongs to the retryable status class |
| `latency_ms` | Latency of this invocation only |
| `cumulative_latency_ms` | Sum of invocation latency for this retry chain |
| `timeout_seconds` | Configured cooperative deadline, or `null` |
| `max_retries` | Maximum retries after the first invocation |

A recovered transient error produces two durable lines. The first is written
and synced before the retry starts:

```json
{"schema_version":"0.4","task_id":"task-1","attempt_index":1,"status":"generation_error","terminal":false,"retryable":true,"max_retries":1}
{"schema_version":"0.4","task_id":"task-1","attempt_index":2,"status":"success","terminal":true,"retryable":false,"max_retries":1}
```

Only `generation_error` and `timeout` are retryable. Invalid tasks, model-load
failures, out-of-memory, and evaluation failures are terminal immediately.
When the retry budget is exhausted, the final retryable failure has
`terminal: true`.

Reports count terminal records as logical warm-up or measurement attempts.
Non-terminal records appear as retry attempts, and cumulative latency keeps
their cost in the final task latency. A run that actually retries is not marked
as a formal performance run because final-attempt usage fields do not represent
the entire retry chain.

## Cooperative timeout boundary

`--attempt-timeout-seconds` is optional and disabled by default. Built-in
Transformers adapters start the deadline after one-time model loading and pass
the remaining budget to `model.generate(max_time=...)`. Media loading,
preprocessing, generation, synchronization, and text decoding are checked
against the same budget.

This is cooperative, not a process kill. Transformers checks its deadline
between generation steps, and an individual CUDA kernel cannot be safely
preempted by Python. Model download/loading is also not interrupted. A custom
adapter must accept and honor the `timeout_seconds` keyword to support this
option. The runner never launches an abandoned background thread that could
continue mutating GPU state after a timeout record is written.

## Phase and repetition

Warm-up:

```json
{
  "schema_version": "0.4",
  "phase": "warmup",
  "repetition": 1,
  "attempt_index": 1,
  "terminal": true,
  "retryable": false,
  "timeout_seconds": null,
  "max_retries": 0,
  "score": null,
  "metric_name": "unscored_warmup"
}
```

Measurement:

```json
{
  "schema_version": "0.4",
  "phase": "measurement",
  "repetition": 2,
  "attempt_index": 1,
  "terminal": true,
  "retryable": false,
  "timeout_seconds": null,
  "max_retries": 0,
  "score": 1.0,
  "metric_name": "normalized_exact_match"
}
```

Warm-up failures and outputs are not hidden. They remain in raw records and the
manifest count, but do not alter measured accuracy or latency aggregates.

## Performance usage fields

Real adapters can add fields under `usage`:

| Field | Unit | Boundary |
|---|---:|---|
| `model_load_ms` | ms | Processor and model dependency/weight loading |
| `media_load_ms` | ms | Media open and input color conversion |
| `preprocessing_ms` | ms | Template, tokenization, tensor creation, device transfer |
| `ttft_ms` | ms | Synchronized generation start to first-token logits |
| `generation_ms` | ms | Complete synchronized model generation |
| `text_decode_ms` | ms | Generated IDs to response text |
| `output_tokens_per_second` | token IDs/s | All generated IDs over generation time |
| `decode_tokens_per_second` | token IDs/s | IDs after the first over post-TTFT time |
| `peak_gpu_memory_mb` | MiB | Maximum CUDA memory allocated during generation |

Unsupported metrics use `null` or are absent; they must not be silently
reported as zero.

## Manifest

For output `runs/example.jsonl`, the CLI creates:

```text
runs/example.jsonl.manifest.json
```

An empty output identity is written with `status: "started"` before inference.
After every JSONL record is flushed and synced to disk, the manifest is
atomically checkpointed with the current record counts, byte length, and
SHA-256. It is finalized to `completed` or `failed`. If a handled interruption
occurs, the failed manifest reconstructs and counts the durable partial
records.

The manifest contains:

- task JSONL and media SHA-256 values;
- task IDs, dataset versions, categories, and order;
- backend, model ID/revision, decoding configuration;
- warm-up and repetition settings;
- timeout, maximum retry count, retryable statuses, and timeout boundary;
- timing and memory definitions;
- OS, Python, packages, CPU/GPU, Git commit and dirty state;
- output status, durable record counts, byte length, and SHA-256.

Repository-relative paths are retained. External absolute paths are reduced to
basename plus content hash to prevent personal paths from entering a published
artifact.

Run artifacts themselves are excluded when the manifest measures Git dirty
state. This prevents a result written inside the repository from making an
otherwise clean run appear dirty; other tracked or untracked changes still
remain visible.

## Output safety and strict resume

The CLI does not silently replace an existing output or manifest:

- choose a new output path for an independent run;
- use `--resume` for a compatible interrupted run;
- use `--overwrite` only when replacement is intentional.

`--resume` accepts only a manifest with `status: "started"` or
`status: "failed"`. Before appending anything, it verifies:

1. task JSONL, media hashes, selected task IDs, categories, and order;
2. backend, model ID/revision, generation options, warm-up, and repetitions;
3. OS, Python, installed runtime packages, GPU, and Git state;
4. the stored output byte length and SHA-256 when the previous attempt
   finalized its manifest;
5. valid UTF-8 JSONL ending on a complete newline-delimited record;
6. that every existing record is the exact prefix of the requested attempt
   plan, including phase, repetition, task, backend, revision, schema, media,
   retry policy, invocation index, terminal state, and cumulative latency.

Only missing invocations are appended. If the last durable record is a
non-terminal retryable failure, resume continues at its next `attempt_index`
instead of restarting or skipping that task. The original creation time remains
in the manifest; `resumed_at_utc` and `resume_count` record recovery history. A
completed run cannot be resumed because an additional experiment should use a
new output path.

A hard process or power loss leaves the last atomic `started` checkpoint. If
the process stops after a record reaches disk but before its manifest
checkpoint, the declared byte length or hash no longer matches and resume is
rejected rather than guessing which state is authoritative. A truncated final
line is likewise rejected rather than discarded.

The SHA-256 is an integrity check, not a digital signature. It detects
accidental or unilateral output changes while the manifest is trusted; an
actor who can rewrite both files can replace both values. Signed provenance is
outside the current local benchmark threat model.

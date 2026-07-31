# Run Records and Manifests

OpenMultimodalLab keeps two complementary artifacts:

- JSONL run records contain one durable result for every attempted invocation;
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

The reporter treats records without `phase` or `repetition` as one measured
legacy repetition. Existing result files remain readable.

## Phase and repetition

Warm-up:

```json
{
  "schema_version": "0.3",
  "phase": "warmup",
  "repetition": 1,
  "score": null,
  "metric_name": "unscored_warmup"
}
```

Measurement:

```json
{
  "schema_version": "0.3",
  "phase": "measurement",
  "repetition": 2,
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
   plan, including phase, repetition, task, backend, revision, schema, and
   media.

Only missing attempts are appended. The original creation time remains in the
manifest; `resumed_at_utc` and `resume_count` record recovery history. A
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

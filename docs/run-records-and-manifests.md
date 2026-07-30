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

The file is written with `status: "started"` before inference and atomically
finalized to `completed` or `failed`. If interruption occurs after records were
flushed, the failed manifest reconstructs and counts those durable partial
records.

The manifest contains:

- task JSONL and media SHA-256 values;
- task IDs, dataset versions, categories, and order;
- backend, model ID/revision, decoding configuration;
- warm-up and repetition settings;
- timing and memory definitions;
- OS, Python, packages, CPU/GPU, Git commit and dirty state;
- output status and durable record counts.

Repository-relative paths are retained. External absolute paths are reduced to
basename plus content hash to prevent personal paths from entering a published
artifact.

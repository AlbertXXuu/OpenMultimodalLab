# Rebuilt formal multimodal benchmark report

This report was generated deterministically from preserved result JSONL and sidecar manifests. It did not rerun a model. Every source passed hash, dataset/media, clean-commit, model-identity, and formal-protocol validation before aggregation.

## Scope

- 2 model backends
- 1 SHA-bound evaluation input
- 4 retained dataset versions
- 102 unique dataset tasks
- exactly one successful warm-up followed by three complete measured repetitions per source
- batch size 1, deterministic decoding, no retries, and no model reloads during measurement

![Formal benchmark overview](overview.svg)

## Run summary

| Dataset | Backend | Tasks | Success | Mean score | Median TTFT | Median throughput | Peak GPU memory |
|---|---|---:|---:|---:|---:|---:|---:|
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | 102 | 306/306 | 0.784 | 120.5 ms | 12.7 tok/s | 4180.5 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | 102 | 306/306 | 0.690 | 260.0 ms | 10.1 tok/s | 1265.3 MiB |

Detailed, machine-readable values are in `run-summary.csv`. Throughput uses each model's native tokenizer and is most reliable for repeated comparisons of the same pinned model.

## Category summary

| Dataset | Backend | Category | Tasks | Success | Mean score | Median TTFT | Peak GPU memory |
|---|---|---|---:|---:|---:|---:|---:|
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `attribute-recognition` | 24 | 72/72 | 0.958 | 109.2 ms | 4089.5 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `chart-qa` | 8 | 24/24 | 0.625 | 164.4 ms | 4179.4 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `counting` | 6 | 18/18 | 1.000 | 105.5 ms | 4089.5 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `document-key-value` | 10 | 30/30 | 0.900 | 165.9 ms | 4180.5 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `document-ocr` | 6 | 18/18 | 0.833 | 172.7 ms | 4179.1 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `event-order` | 4 | 12/12 | 0.000 | 100.5 ms | 4096.0 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `image-description` | 2 | 6/6 | 1.000 | 110.1 ms | 4092.1 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `motion-direction` | 4 | 12/12 | 0.500 | 95.6 ms | 4096.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `occlusion-reasoning` | 3 | 9/9 | 0.667 | 108.6 ms | 4089.8 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `spatial-reasoning` | 10 | 30/30 | 0.800 | 109.5 ms | 4093.4 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `state-change` | 3 | 9/9 | 1.000 | 108.9 ms | 4097.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `table-qa` | 8 | 24/24 | 0.500 | 167.5 ms | 4179.9 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `temporal-counting` | 5 | 15/15 | 0.800 | 99.6 ms | 4097.5 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `temporal-position` | 8 | 24/24 | 0.750 | 110.0 ms | 4097.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `visual-comparison` | 1 | 3/3 | 1.000 | 117.8 ms | 4090.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `attribute-recognition` | 24 | 72/72 | 1.000 | 260.7 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `chart-qa` | 8 | 24/24 | 0.375 | 264.2 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `counting` | 6 | 18/18 | 1.000 | 261.0 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `document-key-value` | 10 | 30/30 | 0.900 | 262.1 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `document-ocr` | 6 | 18/18 | 1.000 | 264.6 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `event-order` | 4 | 12/12 | 0.750 | 174.5 ms | 1177.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `image-description` | 2 | 6/6 | 0.500 | 262.3 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `motion-direction` | 4 | 12/12 | 0.250 | 180.5 ms | 1177.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `occlusion-reasoning` | 3 | 9/9 | 0.333 | 261.3 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `spatial-reasoning` | 10 | 30/30 | 0.533 | 264.0 ms | 1265.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `state-change` | 3 | 9/9 | 0.667 | 167.8 ms | 1177.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `table-qa` | 8 | 24/24 | 0.250 | 262.1 ms | 1265.2 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `temporal-counting` | 5 | 15/15 | 0.400 | 180.9 ms | 1177.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `temporal-position` | 8 | 24/24 | 0.500 | 173.1 ms | 1177.3 MiB |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `visual-comparison` | 1 | 3/3 | 1.000 | 267.8 ms | 1265.2 MiB |

## Failures

No failed measured attempts were recorded. `failures.csv` is still emitted with its stable schema so downstream automation does not need a special case.

## Preserved evidence

| Dataset | Backend | Result | Result SHA-256 | Manifest | Manifest SHA-256 |
|---|---|---|---|---|---|
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `qwen3-vl` | `docs/reports/results/2026-08-10-qwen3-vl-v1.0.0-formal.jsonl` | `a6574423770718fe20f7bd308d09fb8246ed9d0f71a70bd5b15138ff9c90908c` | `docs/reports/results/2026-08-10-qwen3-vl-v1.0.0-formal.manifest.json` | `7b73efc0dececc8d03f998040844ffd122284dd24745907035eb33c8c825cc78` |
| synthetic-docs-v1, synthetic-robustness-v1, synthetic-v1.1, synthetic-video-v1 | `smolvlm2` | `docs/reports/results/2026-08-10-smolvlm2-v1.0.0-formal.jsonl` | `b195dc43e7d0f719c02f819c4ffab8017dd905b74cd7981d4e39bf8527fdb027` | `docs/reports/results/2026-08-10-smolvlm2-v1.0.0-formal.manifest.json` | `cc2c3b4e66b2814475d39c292ce3aec874f0940dac0f5df978777bf6aae9bca9` |

## Rebuild

From the repository root:

```powershell
python scripts/build_benchmark_report.py `
  --input docs/reports/results/2026-08-10-qwen3-vl-v1.0.0-formal.jsonl `
  --input docs/reports/results/2026-08-10-smolvlm2-v1.0.0-formal.jsonl `
  --output-dir <output-directory>
```

Then verify every source, output hash, generator hash, and the self-hashed build manifest:

```powershell
python scripts/build_benchmark_report.py `
  --verify `
  --output-dir <output-directory>
```

## Interpretation limits

These results apply only to the pinned models, task files, media hashes, software environments, and hardware recorded by the source manifests. They are not a universal model ranking and do not represent user preference or production quality.

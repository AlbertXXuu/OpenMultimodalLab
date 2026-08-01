# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Versioned benchmark tasks with required `schema_version: "1.0"`.
- Clear dataset errors for missing and unsupported task schema versions.
- Repeatable `oml run --category` filters with clear no-match errors.
- Reproducible `synthetic-v1` dataset with 10 project-generated PNG tasks.
- Evaluation Protocol v1 covering fairness, timing, failures, and reporting.
- Standard-library image generator plus byte-for-byte reproducibility tests.
- Lazy-loaded Qwen3-VL Transformers adapter with a pinned model revision.
- Typed model-load and out-of-memory result statuses.
- GPU-aware `doctor --backend qwen3-vl` diagnostics.
- Dataset validation errors that include both source line and task ID.
- Preserved first Qwen3-VL ten-task raw run and evidence-based baseline report.
- Task schema 1.1 with explicit, validated deterministic scoring rules.
- Normalized exact-match and ordered or unordered attribute-group scorers.
- Immutable `synthetic-v1.1` correcting prompt/reference alignment defects.
- Run record schema 0.2 with task/dataset versions, metric identity, and details.
- A distinct `evaluation_error` result that preserves successful model output.
- Preserved Qwen3-VL validation run demonstrating 10/10 structured-score matches.
- Auditable warm-up and repeated measurement phases in run record schema 0.3.
- CUDA-synchronized Qwen3-VL TTFT, throughput, preprocessing, and peak-memory metrics.
- Portable run manifests with input hashes, model/config identity, environment, Git state, and durable record counts.
- Median and p95 performance summaries that exclude warm-up attempts.
- Preserved first protocol-compliant Qwen3-VL performance run, manifest, and evidence report.
- Pinned SmolVLM2-500M as a second Apache-2.0 model family for accessible GPU evaluation.
- Shared native Transformers image-text execution, timing, memory, and error contract.
- Lazy-loaded `smolvlm2` backend with explicit BF16 loading and dependency diagnostics.
- Model/processor/chat-template metadata and tokenizer-aware comparison guidance.
- Third-party runtime, model-weight, and synthetic-dataset license inventory.
- Preserved same-commit Qwen3-VL-2B versus SmolVLM2-500M formal comparison.
- Strict `--resume` validation that appends only a compatible run prefix's missing attempts.
- Default output collision protection, explicit `--overwrite`, and per-record atomic manifest checkpoints with output SHA-256/size.
- Standard-library repository audit for text hygiene, local links, JSON/JSONL, secrets, and personal paths.
- Non-duplicated CI with compile, dependency, repository-quality, and wheel-build gates.
- Result-first English project homepage with a complete Simplified Chinese counterpart.
- Copyable first-benchmark tutorial from offline smoke to formal real-model evidence.
- Structured GitHub forms for bugs, model adapters, and dataset/task proposals.
- Pull-request checklist and pre-release security reporting policy.
- Fresh-environment wheel installation and outside-checkout smoke testing in CI.
- Commit-pinned GitHub Actions, enforced by the repository audit, with grouped weekly Dependabot updates.

### Planned

- Per-attempt timeout and bounded retry support.

## [0.1.0] - 2026-07-28

### Added

- Project charter, measurable goals, architecture, roadmap, and weekly workflow.
- Installable Python package and `oml` command-line interface.
- UTF-8 JSONL task loading with duplicate ID and missing media checks.
- Deterministic offline mock adapter.
- Per-task JSONL records, keyword scoring, and aggregate reports.
- Five offline tests and Python 3.11/3.12 CI configuration.

### Known limitations

- No real model backend.
- Keyword coverage is the only evaluator.
- No GPU, token, TTFT, throughput, or memory metrics.

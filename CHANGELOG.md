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

### Planned

- Run manifests.
- Warm-up and detailed performance measurements.

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

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Add a bounded contributor smoke that verifies the installed CLI, mock inference,
  JSON report parity, output hash/size, manifest state, and an enforced socket guard
  in disposable storage; run it in the Linux Python 3.11/3.12 CI matrix.
- Add the post-v1 maintenance policy, portfolio evidence page, and a factual
  fresh-install audit covering the passing Windows quick start, offline build-tool
  prerequisite, and the unavailable Ubuntu venv prerequisite.
- Add a reproducible 1280×640 AlvenX social preview, truthful bilingual
  launch drafts, an external-feedback measurement plan, and an IP/brand
  readiness checklist that avoids unverified ownership or registration claims.
- Add the optional, local-only OpenMultimodalLab interface with an unscored single-media
  playground, read-only JSONL report explorer, bounded uploads, serialized GPU
  access, and the developer signal `ALONICA`.
- Introduce the owner-approved AlvenX public brand while preserving the
  `OpenMultimodalLab` repository, `openmultimodal-lab` package, `oml` CLI, and
  immutable v1.0.0 evidence identities.

### Fixed

- Make Studio Clear reset hidden image/video state, the previous prompt,
  response, metrics, and status without unloading the warm local model.
- Preserve Studio video uploads instead of invoking an undeclared system
  FFmpeg executable to remove audio; document upload boundaries and keep image
  and video previews aspect-safe within bounded heights. Detect HEVC preview
  compatibility separately from model decoding, use safer generation defaults,
  and warn when a response consumes its full output-token allowance. Raise the
  Playground default to 512 tokens and retain 1,024-token retry headroom so
  normal image and video descriptions are less likely to end mid-sentence.
- Reject malformed, incomplete, or non-finite run records with a stable report
  error instead of a traceback or misleading summary.
- Reject blank media references, invalid scoring groups, and duplicate
  case-insensitive scoring references in versioned tasks.

### Changed

- Adopt AlvenX interface standard `2026-08-22.8` across Studio: Instrument Sans,
  the canonical airy light-blue canvas and ink palette, quieter translucent
  evidence surfaces, and the same restrained liquid-glass primary controls as
  alvenx.com. Studio intentionally keeps its background static for sustained
  local work and does not inherit the website's ambient animation.
- Replace narrative-only review coverage for the 32 document and 10 base image
  tasks with task-by-task, reviewer/date/checklist/SHA-bound owner records, so
  all 102 v1.0.0 benchmark task bytes now have machine-validated review
  evidence on `main` without moving or replacing the published release tag.
- Compact the Studio's first viewport, align outer shells, segmented tabs,
  cards, and controls to one nested-radius system, and surface cold-start versus
  warm-model reuse before and after inference. Remove the decorative brand
  container, redundant navigation divider, repeated Workspace title, and
  four-step guide so the working surface starts higher in the initial viewport.
- Refresh English and Chinese public-facing documentation after the Studio
  changes, replacing internal popularity-goal disclaimers with user-oriented setup,
  adoption, and feedback language.
- Use the public outlined AlvenX SVG as the byte-locked Studio wordmark,
  preserving its exact connected-letter geometry, gradient, and color data instead
  of reconstructing the mark with browser text and CSS letter spacing.
- Make the Studio Workspace the default surface, move preserved project context
  to a trailing About tab, and rebalance the rounded input/output panels,
  media preview, response area, advanced controls, and responsive layout.
- Record AlbertXXuu as the public project attribution and AlvenX trademark
  claimant, with ALONICA documented only as a developer ID; add NOTICE,
  TRADEMARKS, and citation metadata without claiming registration.
- Add a privacy-aware first-run feedback template so external adoption can
  become reproducible product evidence instead of an unstructured comment.
- Restyle the OpenMultimodalLab local interface with an explicit light theme, accessible dark text,
  and restrained blue-to-violet gradients limited to the wordmark and hero
  emphasis across desktop and mobile layouts.
- Lock the complete Studio type system to a self-hosted, integrity-bound
  Instrument Sans variable font with its OFL notice, coordinated weights and
  spacing, a single-storey lowercase `a`, tabular evidence figures, and a
  balanced `Al` wordmark treatment across desktop and mobile layouts.
- Lock the owner-approved AlvenX master with connected `Al` and `l–v`, a
  separated `v–e` pair, middle-connected `e–n`, the retained `n–X` signature,
  and one blue-to-indigo-to-violet gradient across `Al`; apply the exact same
  outlined geometry to Studio, README artwork, and the social preview.
- Apply standards-compliant JSON parsing to datasets, run records, resume
  state, run manifests, and the repository audit (`NaN`/`Infinity` are
  rejected).
- Reconcile post-release documentation and define an evidence-led maintenance
  roadmap without treating adoption targets as completed results.
- Preserve verification of immutable v1.0 report bundles after generator code
  evolves by resolving exact source bytes from full local Git history.

## [1.0.0] - 2026-08-10

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
- Privacy-preserving working and Hugging Face model-cache disk checks in `oml doctor`.
- Deterministic README comparison visual generated from preserved formal JSONL evidence.
- Task schema 1.2 with strict, single-answer numeric tolerance scoring.
- Reproducible `synthetic-docs-v1` with 32 OCR, key-value, table, and chart tasks over eight generated PNGs.
- Run record schema 0.4 with durable retry chains, cumulative latency, cooperative Transformers deadlines, and strict retry-aware resume.
- Shared PyAV short-video decoding for both real backends with fixed eight-frame sampling and auditable source metadata.
- Preserved same-commit, 32-task document/table/chart comparison for Qwen3-VL-2B and SmolVLM2-500M.
- Formal-run validation that rejects measurement-phase model reloads after a process restart.
- Bounded dataset, result, manifest, image, and short-video inputs with recorded effective limits.
- Portable run-record media references and Windows/UNC/POSIX absolute-path redaction in durable errors.
- Name-neutral, byte-stable AVI generation for a 24-task short-video draft, with contact sheets and SHA-bound per-task human review validation.
- Name-neutral, byte-stable PNG generation for a 36-task visual-robustness draft covering small objects, low contrast, clutter, and partial occlusion.
- A path-safe, deterministic runtime-license audit with exact package/model versions, PyAV binary hashes, FFmpeg copyleft detection, constraints output, and a CI-validated policy.
- Exact one-warm-up/three-repeat formal-grid validation and a deterministic multi-model report bundle with Markdown, CSV, complete failure data, SVG, source/generator/output hashes, and tamper verification.
- Approved `synthetic-video-v1` with 24 licensed short-video tasks, eight deterministic AVI clips, contact sheets, and a validated SHA-bound owner-review record.
- Approved `synthetic-robustness-v1` with 36 licensed robustness tasks, 12 deterministic PNG images, an overview sheet, and a validated SHA-bound owner-review record.
- A 102-task reviewed v1.0 corpus spanning image, document,
  short-video, and controlled visual-robustness tasks.
- A SHA-256-bound formal-evaluation configuration and builder that assembles
  all 102 approved tasks without introducing a new dataset version.
- Same-commit Qwen3-VL-2B and SmolVLM2-500M formal runs over all 102 reviewed
  image, document, short-video, and robustness tasks, with 612 measured
  attempts, zero runtime failures, and a byte-rebuildable report bundle.
- A factual, reproducible short-video GIF and copyable tutorial built directly
  from the committed formal task and results, including a disclosed model
  failure rather than a cherry-picked all-pass example.
- Final package metadata for the owner-approved `v1.0.0` public version and
  formal GitHub Release.
- Final source-security, dependency-license, Python 3.11/3.13, fresh Windows
  wheel, deterministic rebuild, and GitHub Linux CI evidence, with a strict
  release-readiness gate backed by explicit repository-owner approval.

### Fixed

- Enforced LF checkouts for deterministic CSV report artifacts on Windows.

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

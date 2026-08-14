# `synthetic-docs-v1`: reproducible document, table, and chart tasks

Date: 2026-08-01

## Outcome

OpenMultimodalLab now includes 32 deterministic tasks over eight
project-generated 768×512 PNG images. This is the first document-oriented
dataset slice and expands the repository beyond geometric image tasks without
introducing unclear third-party media rights.

This work releases the dataset and scorer contract. It does **not** claim a
real-model result on these tasks; that requires a separate protocol-compliant
run on a clean commit.

## Why these names and versions

- `synthetic-docs-v1` identifies a stable dataset family and its first released
  content version. A semantic task or media correction will use a new dataset
  version rather than silently changing this file.
- Task schema `1.2` is backward-compatible with 1.0 and 1.1 and adds one new
  scoring contract: `numeric_tolerance`.
- Run record schema remains `0.3` in this change. The separately planned `0.4`
  is reserved for timeout and retry provenance, so dataset work does not
  pretend that runtime reliability work is already complete.

## Coverage matrix

| Category | Tasks | Media | What it exercises |
|---|---:|---:|---|
| Document OCR | 6 | 4 | Identifiers, dates, and visible row counting |
| Document key-value | 10 | 4 | Receipt, invoice, schedule, and project fields |
| Table QA | 8 | 2 | Lookup, extrema, sums, and signed differences |
| Chart QA | 8 | 2 | Bar/line lookup, extrema, sums, gaps, and mean |
| **Total** | **32** | **8 unique** | Four tasks reuse each image |

There are 17 normalized exact-match tasks and 15 numeric-tolerance tasks.
Basic tasks test direct reading; intermediate tasks require one deterministic
arithmetic operation over visible values.

## Task schema 1.2 numeric contract

```json
{
  "schema_version": "1.2",
  "id": "receipt-cafe-total",
  "prompt": "What is the receipt total in dollars? Answer with one number only, without a currency symbol.",
  "media": ["examples/assets/synthetic-docs-v1/receipt-cafe.png"],
  "scoring": {
    "type": "numeric_tolerance",
    "target": 8.37,
    "absolute_tolerance": 0.01
  }
}
```

The target and tolerance must be finite numbers, booleans are rejected, and
the tolerance cannot be negative. The response parser supports signed values,
decimals, and comma-grouped numbers. It deliberately requires exactly one
numeric candidate; zero or multiple candidates score zero. Numeric tasks use
`scoring.target` as their sole reference and reject `expected_keywords`.

Schema 1.0 keyword tasks and schema 1.1 structured tasks continue to load
unchanged. `numeric_tolerance` is rejected under schema 1.1 so consumers can
reason about capabilities from the declared version.

## Reproducibility and licensing

All eight images are produced by
`scripts/generate_synthetic_documents.py` using the Python standard library,
a bundled bitmap font, fixed coordinates, and deterministic PNG compression.
No system font, browser renderer, downloaded asset, or random seed affects the
result. Every task records:

- `source: project-generated`;
- `generator: scripts/generate_synthetic_documents.py`;
- `license: Apache-2.0`;
- dataset version, category, language, difficulty, and answer format.

The regression suite regenerates all images in a temporary directory and
requires byte-for-byte equality with the committed PNG files.

## Review performed

During development, all eight images were inspected at their native resolution.
The review checked title and field legibility, clipping, row/column alignment,
chart labels, plotted values, and agreement between all 32 references and the
visible source values. That review found one layout defect—accent bars covering
the first character of key-value labels—which was fixed before this report.

Update on 2026-08-14: `AlbertXXuu` re-reviewed all eight original images and
all 32 tasks using the same task-by-task checklist as the other final datasets.
The approved record is
[`docs/reviews/synthetic-docs-v1.json`](../reviews/synthetic-docs-v1.json) and
is bound to dataset SHA-256
`79b9f2c25f2985b6ccbd6fba2e44d234685338534d3d810f4f2931eacdb9d610`.

Automated checks additionally verify:

- exactly 32 unique tasks and eight unique media files;
- exactly four tasks per image;
- the expected category distribution;
- required license and generator metadata;
- schema/scorer compatibility and numeric field validation;
- deterministic media regeneration.

## Known limits

- The images are clean, high-contrast, English-only synthetic documents.
- There are eight unique semantic layouts, with four questions per image.
- The set does not yet test rotation, blur, handwriting, dense multipage
  documents, multilingual OCR, or adversarial chart design.
- No score from the `mock` backend is model-quality evidence.
- No Qwen3-VL or SmolVLM2 result on this dataset is published in this change.

## Reproduce the dataset check

```powershell
.\.venv\Scripts\python.exe scripts/generate_synthetic_documents.py
.\.venv\Scripts\python.exe -m unittest tests.test_example_datasets tests.test_datasets tests.test_metrics -v

.\.venv\Scripts\oml.exe run `
  --dataset examples/tasks/synthetic-docs-v1.jsonl `
  --output runs/synthetic-docs-v1-mock.jsonl
```

The next evidence step is a clean-commit real-model run under the existing
warm-up and three-repetition protocol. The broader roadmap remains at least
100 human-checked tasks and includes short-video coverage.

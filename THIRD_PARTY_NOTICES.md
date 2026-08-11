# Third-Party Notices

OpenMultimodalLab source code and project-generated synthetic media are
licensed under Apache-2.0. Real-model support is optional and installs
independent third-party packages and model weights under their own terms.

## Vendored interface font

Ailumetra Studio embeds the unmodified Instrument Sans variable webfont for
offline, deterministic interface rendering:

| Asset | Upstream revision | SHA-256 | License |
|---|---|---|---|
| `InstrumentSans[wdth,wght].woff2` | `7fa22308a3d0c94ee2b3cd537a1196b65db34a3e` | `aa72922aafcc0dc18f36ec1d805b0212057dabe8b9d5b8b57f67035aea1b826d` | SIL OFL 1.1 |

Upstream source: <https://github.com/Instrument/instrument-sans>. The exact
license text is distributed at
`src/openmultimodal_lab/assets/fonts/InstrumentSans-OFL.txt`. The WOFF2 bytes
are base64-wrapped only so the source distribution and wheel can load the font
without a network request; the decoded upstream bytes are unchanged. The font
license applies to the font software, not to the Apache-2.0 project source.

This file records the dependency and model-license evidence reviewed for the
final Windows Python 3.11 candidate environment on 2026-08-10. It is an
engineering inventory, not legal advice. The project does not vendor these
packages or model weights.

## Optional Python runtime

The post-v1.0 Ailumetra Studio extra uses Gradio as a separately installed UI
dependency. The development environment verified Gradio 6.22.0, whose package
metadata declares Apache-2.0. It is not vendored, bundled, or part of the
historical v1.0.0 runtime snapshot. A future release must refresh the complete
runtime-license audit and constraints rather than treating this note as release
evidence.

The following values come from the installed package metadata in the verified
Python 3.11 model environment:

| Package | Verified version | Declared license metadata | Used by |
|---|---:|---|---|
| `accelerate` | 1.14.0 | Apache | Both real backends |
| [`av`](https://github.com/PyAV-Org/PyAV) | 18.0.0 | BSD-3-Clause | Deterministic local video decoding |
| `huggingface-hub` | 1.25.1 | Apache-2.0 | Pinned model download and cache |
| `num2words` | 0.5.14 | LGPL | SmolVLM2 processor |
| `numpy` | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Bounded video sampling and array runtime |
| `pillow` | 12.3.0 | MIT-CMU | Image loading |
| `safetensors` | 0.8.0 | Apache | Model-weight loading |
| `tokenizers` | 0.22.2 | Apache | Native tokenizer runtime |
| `torch` | 2.13.0+cu130 | Composite SPDX expression in package metadata | Model inference |
| `torchvision` | 0.28.0+cu130 | BSD | Vision runtime |
| `transformers` | 5.14.1 | Apache 2.0 | Model and processor loading |

Version ranges in `pyproject.toml` may resolve to different releases in a new
environment. The exact verified baseline is retained at
`requirements/model-windows-py311-constraints.txt`, and the machine-readable
package and binary inventory is retained at
`docs/reports/results/final-runtime-license-audit.json`.
Redistributors must retain upstream license files when their distribution
method requires them.

The LGPL dependency is dynamically imported from the user's Python
environment; its source is not copied into this repository or linked into a
redistributed binary. Users who redistribute a bundled application must
perform their own compliance review.

PyAV binary wheels bundle FFmpeg components. The verified PyAV 18.0.0 Windows
wheel contains `libx264`, `libx265`, and OpenCORE AMR DLLs. Under FFmpeg's
published external-library rules, the conservative effective classification
for this binary combination is `GPL-3.0-or-later`, distinct from PyAV's own
BSD-3-Clause source license. OpenMultimodalLab does not vendor or redistribute
the wheel or those DLLs. The public v1.0 must remain source-only; anyone
redistributing a bundled runtime or executable must perform a separate
compliance review. The exact binaries, versions, and hashes are captured by the
final runtime snapshot generated with
[`scripts/audit_runtime_licenses.py`](scripts/audit_runtime_licenses.py).

## Model weights and processors

Model files are downloaded separately from their upstream repositories and
are never committed to this repository:

| Model | Pinned revision | Declared model-card license |
|---|---|---|
| [`Qwen/Qwen3-VL-2B-Instruct`](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) | `89644892e4d85e24eaac8bacfd4f463576704203` | Apache-2.0 |
| [`HuggingFaceTB/SmolVLM2-500M-Video-Instruct`](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct) | `7b375e1b73b11138ff12fe22c8f2822d8fe03467` | Apache-2.0 |

Users remain responsible for reviewing the complete upstream model card,
acceptable-use terms, and laws applicable to their inputs and outputs.

## Dataset and media

The canonical `synthetic-v1.1`, `synthetic-docs-v1`, `synthetic-video-v1`, and
`synthetic-robustness-v1` tasks and media are project-generated and declare
`license: "Apache-2.0"` in every task. Their generators and reproducibility
tests are included in the repository. The 24 short-video tasks and 36 visual
robustness tasks additionally have SHA-bound owner-review records. No
third-party image or video is copied into these datasets.

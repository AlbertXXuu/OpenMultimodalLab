# Third-Party Notices

OpenMultimodalLab source code and project-generated synthetic media are
licensed under Apache-2.0. Real-model support is optional and installs
independent third-party packages and model weights under their own terms.

This file records the dependency and model-license evidence reviewed for the
local baseline environment through 2026-08-02. It is an engineering inventory,
not legal advice. The project does not vendor these packages or model weights.

## Optional Python runtime

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
environment. Before a public release, regenerate this inventory from the
actual lock or baseline environment and retain upstream license files when
redistribution requires them.

The LGPL dependency is dynamically imported from the user's Python
environment; its source is not copied into this repository or linked into a
redistributed binary. Users who redistribute a bundled application must
perform their own compliance review.

PyAV binary wheels include or link FFmpeg components. OpenMultimodalLab does
not vendor or redistribute those wheels. Anyone redistributing a bundled
runtime must audit the exact PyAV wheel and its FFmpeg build in addition to the
PyAV BSD-3-Clause package license.

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

The committed `synthetic-v1`, `synthetic-v1.1`, and `synthetic-docs-v1` tasks
and PNG files are project-generated and declare `license: "Apache-2.0"` in
every task. Their generators and byte-for-byte regeneration tests are included
in the repository. No third-party image or video is copied into these
datasets. A licensed short-video dataset has not yet been committed.

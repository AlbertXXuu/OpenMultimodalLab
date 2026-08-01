# Security review: bounded local inputs and durable-path privacy

Date: 2026-08-02

## Executive summary

Scope: the Python CLI, dataset/result parsers, local image/video adapters,
durable artifacts, model loading, subprocess use, GitHub Actions, and security
documentation. OpenMultimodalLab has no Web server, remote API backend, account
system, or upload endpoint, so Web authentication, cookies, CORS, and TLS are
outside the current threat model.

No critical or high-severity finding was identified. Two medium-severity local
risks were fixed in this change: unbounded parser inputs and absolute local
paths entering shareable run records. Native media decoders, dependency
resolution drift, and cooperative-only CUDA timeouts remain documented residual
risks. This review is an engineering assessment, not a claim of perfect
security or legal advice.

## Threat model

The expected user runs a local CLI against a JSONL task file and local media.
Relevant assets are:

- local files and usernames encoded in paths;
- GPU/CPU memory and execution time;
- model and package supply-chain integrity;
- benchmark results intended for later sharing;
- GitHub workflow credentials and repository contents.

The main untrusted boundaries are JSONL, Pillow image decoding, PyAV/FFmpeg
video probing and decoding, downloaded model artifacts, and text returned in
third-party exceptions. A malicious user who already controls the local Python
process is out of scope.

## Fixed findings

### SEC-001 — Medium — local input size and decode-work exhaustion

Impact: a tiny or malformed task/media input could previously cause excessive
memory use or prolonged native decoding before inference began.

The following fixed limits are now enforced:

- dataset: 16 MiB total and 1 MiB per JSONL line
  (`src/openmultimodal_lab/datasets.py:13`);
- report/resume output: 256 MiB total and 4 MiB per record
  (`src/openmultimodal_lab/reporting.py:14`,
  `src/openmultimodal_lab/runner.py:24`);
- manifest: 8 MiB (`src/openmultimodal_lab/manifest.py:21`);
- image: 32 MiB and 40 million decoded pixels
  (`src/openmultimodal_lab/adapters/transformers_image_text.py:25`,
  `src/openmultimodal_lab/adapters/transformers_image_text.py:380`);
- short video: 256 MiB, 60 seconds, 3,600 frames, and 3840×2160 pixels/frame
  (`src/openmultimodal_lab/adapters/transformers_image_text.py:27`,
  `src/openmultimodal_lab/adapters/transformers_image_text.py:320`).

Video metadata is validated inside the Transformers sampling callback, before
PyAV decodes through the selected final index. Successful records expose the
effective boundaries in `usage.media_limits`
(`src/openmultimodal_lab/adapters/transformers_image_text.py:705`). Manifest
construction also refuses to hash more than 256 MiB from any media input,
preventing oversized files from consuming unbounded I/O before adapter
validation.

### SEC-002 — Medium — personal paths in durable run artifacts

Impact: a task containing an absolute media path, or a dependency exception
containing a cache path, could reveal a username or local directory when the
JSONL result was shared.

Relative media references remain unchanged; absolute Windows, UNC, and POSIX
references are reduced to their basenames
(`src/openmultimodal_lab/privacy.py:35`). Absolute local paths are redacted
from stored errors (`src/openmultimodal_lab/privacy.py:44`). The runner applies
both rules to
success, failure, warm-up, evaluation-error, and strict-resume paths
(`src/openmultimodal_lab/runner.py:221`,
`src/openmultimodal_lab/runner.py:400`). Dataset and adapter diagnostics also
avoid printing resolved media directories.

## Existing controls reviewed

- Real adapters use pinned model revisions and do not request remote custom
  code (`src/openmultimodal_lab/adapters/transformers_image_text.py:129`).
- Model weights and caches are not stored in the repository; raw `runs/` and
  common secret files are ignored.
- `git` and `nvidia-smi` subprocesses use fixed argument arrays, no shell, a
  timeout, and captured output (`src/openmultimodal_lab/manifest.py:65`,
  `src/openmultimodal_lab/cli.py:192`).
- GitHub Actions has read-only repository contents permission and every remote
  action is pinned to a full commit (`.github/workflows/ci.yml:8`,
  `.github/workflows/ci.yml:29`).
- The repository audit checks common credentials, private-key headers,
  personal paths, immutable Action refs, UTF-8, JSON/JSONL, and local links.
- Existing outputs use atomic manifest replacement and `fsync`; resume verifies
  record prefix, hashes, byte size, model/configuration, environment, and Git
  state before appending.

## Residual risks

### SEC-003 — Medium — native media parsers are not sandboxed

Pillow, PyAV, and the FFmpeg libraries behind PyAV process untrusted binary
formats in the benchmark process. Size/duration/dimension limits reduce denial
of service but do not contain a vulnerability in native decoder code.

Mitigation: keep those dependencies current, use project-generated media for
published benchmarks, and inspect unknown third-party files in a disposable
environment. Process isolation is a possible post-v1 hardening feature.

### SEC-004 — Medium — optional dependency resolution can drift

`pyproject.toml` declares compatible lower bounds rather than a lock. Every
formal manifest records exact installed versions, but a future install can
resolve different package or binary builds. PyAV wheels also carry an FFmpeg
licensing and vulnerability surface not described by PyAV's package license
alone.

Mitigation before public v1.0: regenerate the installed dependency/license
inventory from the final clean environment, preserve a reproducible baseline
constraints file, and audit the exact PyAV/FFmpeg build. This remains an open
public-release gate.

### SEC-005 — Low — inference timeout is cooperative

Transformers `max_time` and adapter checks cannot safely terminate a CUDA
kernel already executing. A pathological local model invocation can therefore
exceed the requested deadline.

Mitigation: retain the documented cooperative boundary and run untrusted or
experimental configurations under an external process supervisor. Do not
retry an abandoned CUDA thread in the same process.

## Verification

The post-fix full-model diagnostic used one temporary, project-generated,
two-second 96×64 MP4 with 16 source frames. Both pinned backends accepted the
bounded sampling callback and consumed exact indexes `0, 2, 4, 6, 8, 10, 12,
14`. Qwen3-VL recorded 4,082.0 MiB peak allocated VRAM and 520.6 ms TTFT;
SmolVLM2 recorded 1,179.3 MiB and 243.6 ms. Both answered `left` even though
the red square moved right. This proves the safety/runtime integration only;
it is an intentionally disclosed quality failure, not formal benchmark
evidence. The pinned SmolVLM2 top-level config emits an invalid pad-token
warning during loading; generation explicitly used the processor tokenizer's
valid ID `2` (and Qwen used `151643`), with both effective values retained in
`usage.pad_token_id`.

Automated regression coverage includes:

- dataset, record, and manifest oversize rejection;
- invalid UTF-8 rejection with safe line diagnostics;
- media-size rejection before model loading;
- video duration/frame/dimension validation before decoding;
- identical bounded sampling for both real adapters;
- absolute media and error-path redaction in persisted JSONL;
- byte-stable published evidence and the existing repository privacy audit.

Final v1.0 security sign-off still requires rerunning the complete test suite,
fresh-wheel checks, dependency/license inventory, and public-release readiness
matrix after the task corpus and video evidence are complete.

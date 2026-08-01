# Reproducible runtime-license audit

OpenMultimodalLab is released as source code. It does not vendor model weights,
Python wheels, CUDA libraries, FFmpeg libraries, or a prebuilt runtime. This
boundary is important: the optional PyAV wheel contains binary dependencies
whose effective license differs from PyAV's own package license.

This is an engineering compliance check, not legal advice.

## Permanent policy and checker

The reviewable policy is
[`docs/license-audit-policy.json`](license-audit-policy.json). It records:

- the exact Python 3.11 packages required by the verified ML environment;
- accepted installed-package license declarations and their risk tiers;
- the two model IDs, immutable revisions, licenses, and source pages;
- expected PyAV and linked FFmpeg library versions;
- GPL, version-3, and nonfree binary markers;
- the source-only distribution decision and forbidden tracked binary suffixes.

CI validates the policy without installing ML dependencies:

```powershell
.\.venv\Scripts\python.exe scripts/audit_runtime_licenses.py `
  --validate-policy-only
```

The full audit reads installed package `METADATA` directly through Python's
standard library. It does not depend on terminal encoding, so an emoji or
non-ASCII author field cannot break JSON generation on a Chinese Windows code
page. It omits installation paths and user names from durable output.

## Preliminary Windows ML audit

Run from the dedicated Python 3.11 environment:

```powershell
.\.venv-ml\Scripts\python.exe scripts/audit_runtime_licenses.py `
  --output runs/runtime-license-audit.json `
  --constraints-output runs/model-env-constraints.txt
```

The 2026-08-02 preliminary run reported:

```text
License audit PASS: 44 packages, 25 PyAV binaries, 0 finding(s), 2 warning(s)
```

The warnings are required and cannot be suppressed by changing a Markdown
claim. They identify accepted MPL/LGPL package metadata and the installed
PyAV 18.0.0 Windows wheel's `libx264`, `libx265`, `libopencore-amrnb`, and
`libopencore-amrwb` components. The snapshot hashes every bundled binary and
records the seven linked FFmpeg library versions.

## Why the PyAV and FFmpeg licenses differ

PyAV declares BSD-3-Clause and its official installation documentation says
that PyPI wheels bundle FFmpeg. FFmpeg is normally LGPL-2.1-or-later, but its
official license documentation states:

- combining FFmpeg with x264 or x265 requires GPL;
- combining the listed Apache-2.0 libraries, including OpenCORE, requires
  upgrading the license combination to version 3;
- `--enable-nonfree` builds are not redistributable.

The current wheel's binary evidence therefore receives the conservative
effective classification `GPL-3.0-or-later`. No `libfdk` nonfree marker was
found. The project may depend on this user-installed runtime while preserving
its own Apache-2.0 source license, but it must not attach the environment,
wheel, DLLs, or a bundled executable to a source-only release without a new
distribution-specific compliance review.

Primary sources:

- [PyAV repository and bundled-wheel installation statement](https://github.com/PyAV-Org/PyAV)
- [PyAV BSD-3-Clause license](https://pyav.org/docs/stable/development/license.html)
- [PyAV FFmpeg binary-build source at the reviewed commit](https://github.com/PyAV-Org/pyav-ffmpeg/tree/d7a92d1c8149eb47357337b62a0136cd15ae4781)
- [FFmpeg legal and LGPL/GPL compliance guidance](https://ffmpeg.org/legal.html)
- [FFmpeg license and external-library rules](https://ffmpeg.org/doxygen/trunk/md_LICENSE.html)

## Final-candidate procedure

After the canonical corpus, reports, and version metadata are complete, begin
from a clean commit and run:

```powershell
.\.venv-ml\Scripts\python.exe scripts/audit_runtime_licenses.py `
  --require-clean `
  --output docs/reports/results/final-runtime-license-audit.json `
  --constraints-output requirements/model-windows-py311-constraints.txt
```

Then review the generated package versions, license classifications, model
records, FFmpeg binaries, warnings, and snapshot SHA-256. Write
`docs/reports/final-dependency-license-audit.md` with the command, source
commit, constraints hash, snapshot hash, distribution boundary, reviewer, and
date.

The signed report must include these exact machine-checked fields:

```markdown
# Final dependency and license audit

Outcome: PASS

Reviewer: <human reviewer name>

Review date: YYYY-MM-DD

Snapshot SHA-256: `<exact snapshot_sha256 value>`
```

The public-readiness checker will only pass `FINAL-LICENSE-AUDIT` when all
three artifacts exist and the JSON proves:

- `status: PASS`, no findings, and a valid self-hash;
- a clean 40-character source commit with no tracked runtime binaries;
- at least two Apache-2.0 model records with immutable revisions;
- the expected GPL and version-3 FFmpeg markers and no nonfree marker;
- a non-empty package inventory and the source-only distribution boundary.

A standalone report file is deliberately insufficient.

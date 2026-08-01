# Security Policy

## Supported state

OpenMultimodalLab is in pre-release development. Security fixes are applied to
the current `main` branch; no stable release line is supported yet.

## Report a vulnerability

Do not open a public issue containing an exploit, credential, private media,
personal path, or other sensitive evidence.

Use the repository **Security** tab and choose **Report a vulnerability** when
private vulnerability reporting is available. If that option is unavailable,
open a minimal public issue asking the maintainer to establish a private
contact channel. Do not include vulnerability details in that issue.

Include privately:

- affected commit and platform;
- impact and realistic threat model;
- minimal reproduction with synthetic data;
- whether local files, model caches, credentials, or remote services are
  involved;
- suggested mitigation, if known.

No response-time or embargo SLA is promised during pre-release development.
Please allow the maintainer to confirm impact and coordinate a fix before
public disclosure.

## Current security boundaries

- Core benchmark execution is local-first and does not upload media.
- No remote API backend is currently enabled by default.
- Model downloads use the repositories and immutable revisions documented by
  each backend.
- User outputs and model caches are excluded from Git.
- Dataset JSONL is limited to 16 MiB with 1 MiB per line; report JSONL is
  limited to 256 MiB with 4 MiB per record; resume manifests are limited to
  8 MiB.
- Images are limited to 32 MiB and 40 million decoded pixels. Videos are
  limited to 256 MiB, 60 seconds, 3,600 source frames, and 3840×2160 pixels
  per frame before the fixed eight-frame sample is decoded.
- Durable run records keep relative media references and reduce absolute media
  paths to basenames. Windows drive, UNC, and POSIX absolute paths are redacted
  from persisted error text.
- The repository audit detects common credentials and personal paths, but it
  is not a complete secret-scanning or malware-analysis system.
- Images, documents, and videos remain untrusted native-parser inputs. The
  limits reduce resource-exhaustion exposure but do not sandbox Pillow, PyAV,
  FFmpeg, PyTorch, or Transformers. Use current dependency builds and process
  untrusted files in a disposable environment.

## Safe public bug reports

For non-sensitive defects, use the Bug report issue form and replace local
paths, usernames, tokens, and private media with synthetic placeholders.

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
- The repository audit detects common credentials and personal paths, but it
  is not a complete secret-scanning or malware-analysis system.
- Images and future document/video inputs must still be treated as untrusted
  files; size, parser, and processing-time limits remain required roadmap work.

## Safe public bug reports

For non-sensitive defects, use the Bug report issue form and replace local
paths, usernames, tokens, and private media with synthetic placeholders.

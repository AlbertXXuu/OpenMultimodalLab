# Doctor disk-readiness check

Date: 2026-08-01

Outcome: `oml doctor` now reports usable disk headroom for both benchmark
outputs and the Hugging Face model cache without exposing the cache path.

## Motivation

The first real-model download is one of the most common failure points on a
consumer machine. Checking only GPU memory can leave a user with a partial
multi-gigabyte download and an unclear error. Disk readiness belongs beside
Python, CUDA, BF16, and optional-package diagnostics.

## Behavior

Every doctor run reports free space on the working-directory disk. Real-model
checks also resolve the effective Hugging Face Hub cache location in this
order:

1. `HF_HUB_CACHE`;
2. `HF_HOME/hub`;
3. `XDG_CACHE_HOME/huggingface/hub`;
4. the platform user's default Hugging Face cache.

Only free GiB is printed. The path itself is intentionally omitted because
doctor output is commonly pasted into bug reports and local cache paths can
contain a username or organization-specific layout.

| Backend | Warning threshold | Basis |
|---|---:|---|
| Qwen3-VL-2B | 8.0 GiB free | 3.96GB weight plus download/cache headroom |
| SmolVLM2-500M | 4.0 GiB free | roughly 2GB download plus headroom |

A low-space result is advisory. Existing weights may already be cached, so it
does not override successful dependency and GPU readiness checks. If disk
usage cannot be queried, doctor prints `unavailable` and continues instead of
crashing.

## Automated evidence

Tests cover:

- environment-variable precedence for the cache location;
- unavailable disk information remaining non-fatal for the core;
- a 2.0 GiB cache disk producing the Qwen 8.0 GiB recommendation;
- existing CUDA, BF16, missing-module, and CPU-only-PyTorch diagnostics.

The implementation uses only `os`, `pathlib`, and `shutil`; the dependency-free
core contract remains unchanged.

## Limits

- Free space is a point-in-time filesystem measurement, not a reservation.
- The thresholds are setup recommendations, not exact model-size guarantees.
- The check does not prove that a cached model is complete or untampered.
- Future document/video datasets still need per-input size and processing-time
  limits before untrusted media can be treated as safe.

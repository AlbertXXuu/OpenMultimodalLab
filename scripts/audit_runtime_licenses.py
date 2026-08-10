"""Create a deterministic license audit for the installed ML runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from importlib import metadata
from pathlib import Path
from typing import Any


MAX_POLICY_BYTES = 1024 * 1024
MAX_METADATA_BYTES = 4 * 1024 * 1024
NAME_SEPARATORS = re.compile(r"[-_.]+")


def canonicalize_name(value: str) -> str:
    """Return the PEP 503 normalized distribution name."""

    return NAME_SEPARATORS.sub("-", value).lower()


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _bounded_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw = handle.read(MAX_POLICY_BYTES + 1)
    if len(raw) > MAX_POLICY_BYTES:
        raise ValueError("license policy exceeds the 1 MiB safety limit")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("license policy must be a JSON object")
    return value


def resolve_declared_license(package_metadata: Mapping[str, Any]) -> str:
    """Prefer PEP 639, then short legacy metadata, then classifiers."""

    expression = package_metadata.get("License-Expression")
    if isinstance(expression, str) and expression.strip():
        return _normalized_text(expression)

    legacy = package_metadata.get("License")
    if isinstance(legacy, str) and legacy.strip() and len(legacy) <= 256:
        return _normalized_text(legacy)

    get_all = getattr(package_metadata, "get_all", None)
    classifiers = get_all("Classifier", []) if callable(get_all) else []
    license_values = [
        value.rsplit("::", maxsplit=1)[-1].strip()
        for value in classifiers
        if isinstance(value, str) and value.startswith("License :: ")
    ]
    return " OR ".join(dict.fromkeys(license_values))


def classify_license(
    declared_license: str,
    rules: Sequence[Mapping[str, Any]],
) -> tuple[str | None, str | None]:
    for rule in rules:
        values = rule.get("declared_values", [])
        if declared_license in values:
            normalized = rule.get("normalized")
            tier = rule.get("tier")
            if isinstance(normalized, str) and isinstance(tier, str):
                return normalized, tier
    return None, None


def validate_policy(policy: Mapping[str, Any]) -> list[str]:
    """Validate policy structure without requiring the ML environment."""

    findings: list[str] = []
    if policy.get("schema_version") != "1.0":
        findings.append("policy schema_version must be '1.0'")
    if policy.get("distribution_scope") != "source-only-no-runtime-binaries":
        findings.append("policy must declare the source-only distribution scope")
    python_minors = policy.get("python_minors")
    if not isinstance(python_minors, list) or not python_minors:
        findings.append("policy python_minors must be a non-empty list")

    required = policy.get("required_packages")
    if not isinstance(required, dict) or not required:
        findings.append("policy required_packages must be a non-empty object")
    else:
        for name, version in required.items():
            if name != canonicalize_name(name):
                findings.append(f"required package name is not canonical: {name}")
            if not isinstance(version, str) or not version.strip():
                findings.append(f"required package {name} has no version")

    allowed_tiers = policy.get("allowed_package_license_tiers")
    if not isinstance(allowed_tiers, list) or not allowed_tiers:
        findings.append("policy allowed license tiers must be a non-empty list")
        allowed_tier_values: set[str] = set()
    else:
        allowed_tier_values = set(allowed_tiers)
        if len(allowed_tier_values) != len(allowed_tiers):
            findings.append("policy allowed license tiers contain duplicates")

    rules = policy.get("license_rules")
    declared_seen: set[str] = set()
    if not isinstance(rules, list) or not rules:
        findings.append("policy license_rules must be a non-empty list")
    else:
        for index, rule in enumerate(rules, start=1):
            if not isinstance(rule, dict):
                findings.append(f"policy license rule {index} must be an object")
                continue
            values = rule.get("declared_values")
            if not isinstance(values, list) or not values:
                findings.append(
                    f"policy license rule {index} has no declared values"
                )
                continue
            for value in values:
                if not isinstance(value, str) or not value.strip():
                    findings.append(
                        f"policy license rule {index} contains an invalid value"
                    )
                elif value in declared_seen:
                    findings.append(
                        f"policy license value appears more than once: {value}"
                    )
                else:
                    declared_seen.add(value)
            if rule.get("tier") not in allowed_tier_values:
                findings.append(
                    f"policy license rule {index} uses a disallowed tier"
                )
            if (
                not isinstance(rule.get("normalized"), str)
                or not rule["normalized"].strip()
            ):
                findings.append(
                    f"policy license rule {index} has no normalized value"
                )

    ffmpeg = policy.get("ffmpeg")
    if not isinstance(ffmpeg, dict):
        findings.append("policy ffmpeg section must be an object")
    else:
        if ffmpeg.get("bundled_runtime_allowed") is not False:
            findings.append("policy must forbid bundled PyAV/FFmpeg runtime")
        versions = ffmpeg.get("expected_library_versions")
        if not isinstance(versions, dict) or not versions:
            findings.append("policy ffmpeg library versions must be an object")
        else:
            for name, version in versions.items():
                if (
                    not isinstance(name, str)
                    or not isinstance(version, list)
                    or len(version) != 3
                    or not all(
                        isinstance(item, int) and not isinstance(item, bool)
                        for item in version
                    )
                ):
                    findings.append(
                        f"policy ffmpeg library version is invalid: {name}"
                    )
        for key in (
            "gpl_binary_markers",
            "version3_binary_markers",
            "nonfree_binary_markers",
        ):
            markers = ffmpeg.get(key)
            if (
                not isinstance(markers, list)
                or not markers
                or not all(
                    isinstance(marker, str) and marker.strip()
                    for marker in markers
                )
                or len(markers) != len(set(markers))
            ):
                findings.append(f"policy ffmpeg {key} must be unique strings")
        for key in (
            "official_legal_url",
            "official_license_url",
            "pyav_binary_build_source",
        ):
            url = ffmpeg.get(key)
            if not isinstance(url, str) or not url.startswith("https://"):
                findings.append(f"policy ffmpeg {key} must be an HTTPS URL")
        if ffmpeg.get("gpl_effective_license") != "GPL-3.0-or-later":
            findings.append("policy ffmpeg effective GPL license is invalid")

    models = policy.get("models")
    if not isinstance(models, list) or len(models) < 2:
        findings.append("policy must contain at least two model records")
    else:
        model_ids: set[str] = set()
        for index, model in enumerate(models, start=1):
            if not isinstance(model, dict):
                findings.append(f"policy model {index} must be an object")
                continue
            model_id = model.get("model_id")
            if not isinstance(model_id, str) or not model_id.strip():
                findings.append(f"policy model {index} has no model_id")
            elif model_id in model_ids:
                findings.append(f"policy model is duplicated: {model_id}")
            else:
                model_ids.add(model_id)
            if not re.fullmatch(r"[0-9a-f]{40}", str(model.get("revision", ""))):
                findings.append(
                    f"policy model {index} revision is not an immutable SHA"
                )
            if model.get("license") != "Apache-2.0":
                findings.append(
                    f"policy model {index} license is not Apache-2.0"
                )
            source = model.get("source")
            if not isinstance(source, str) or not source.startswith("https://"):
                findings.append(f"policy model {index} source is not HTTPS")

    suffixes = policy.get("forbidden_tracked_suffixes")
    if (
        not isinstance(suffixes, list)
        or not suffixes
        or not all(
            isinstance(suffix, str)
            and suffix.startswith(".")
            and suffix == suffix.lower()
            for suffix in suffixes
        )
        or len(suffixes) != len(set(suffixes))
    ):
        findings.append("policy forbidden tracked suffixes must be non-empty")
    return sorted(findings)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_bytes(distribution: metadata.Distribution) -> bytes:
    value = distribution.read_text("METADATA")
    if value is None:
        value = distribution.read_text("PKG-INFO")
    if value is None:
        return b""
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_METADATA_BYTES:
        raise ValueError("installed package metadata exceeds 4 MiB")
    return encoded


def collect_installed_packages(
    distributions: Iterable[metadata.Distribution] | None = None,
) -> list[dict[str, Any]]:
    """Collect path-free, deterministic installed-distribution evidence."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    source = metadata.distributions() if distributions is None else distributions
    for distribution in source:
        raw_name = distribution.metadata.get("Name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        name = canonicalize_name(raw_name)
        license_files = sorted(
            {
                Path(value).as_posix()
                for value in distribution.metadata.get_all("License-File", [])
                if isinstance(value, str) and value.strip()
            }
        )
        grouped.setdefault(name, []).append(
            {
                "version": distribution.version,
                "declared_license": resolve_declared_license(
                    distribution.metadata
                ),
                "license_files": license_files,
                "metadata_sha256": _sha256_bytes(
                    _metadata_bytes(distribution)
                ),
            }
        )

    packages: list[dict[str, Any]] = []
    for name in sorted(grouped):
        records = grouped[name]
        versions = sorted({record["version"] for record in records})
        declared = sorted(
            {record["declared_license"] for record in records}
        )
        license_files = sorted(
            {
                item
                for record in records
                for item in record["license_files"]
            }
        )
        metadata_hashes = sorted(
            {record["metadata_sha256"] for record in records}
        )
        packages.append(
            {
                "name": name,
                "versions": versions,
                "declared_licenses": declared,
                "license_files": license_files,
                "metadata_sha256s": metadata_hashes,
            }
        )
    return packages


def audit_packages(
    packages: Sequence[dict[str, Any]],
    policy: Mapping[str, Any],
) -> list[str]:
    findings: list[str] = []
    rules = policy.get("license_rules", [])
    allowed_tiers = set(policy.get("allowed_package_license_tiers", []))
    by_name = {package["name"]: package for package in packages}

    for package in packages:
        if len(package["versions"]) != 1:
            findings.append(
                f"package {package['name']} has conflicting installed "
                f"versions {package['versions']}"
            )
        if len(package["declared_licenses"]) != 1:
            findings.append(
                f"package {package['name']} has conflicting license "
                f"metadata {package['declared_licenses']}"
            )
        classifications: list[dict[str, str]] = []
        for declared in package["declared_licenses"]:
            normalized, tier = classify_license(declared, rules)
            if normalized is None or tier is None:
                findings.append(
                    f"package {package['name']} has unreviewed license "
                    f"metadata {declared!r}"
                )
                continue
            classifications.append(
                {
                    "declared": declared,
                    "normalized": normalized,
                    "tier": tier,
                }
            )
            if tier not in allowed_tiers:
                findings.append(
                    f"package {package['name']} uses disallowed tier {tier}"
                )
        package["license_classifications"] = classifications

    required = policy.get("required_packages", {})
    for name, expected_version in sorted(required.items()):
        package = by_name.get(canonicalize_name(name))
        if package is None:
            findings.append(f"required package {name} is not installed")
            continue
        if package["versions"] != [expected_version]:
            findings.append(
                f"required package {name} versions {package['versions']} "
                f"do not match {expected_version}"
            )
    return findings


def analyze_binary_names(
    names: Sequence[str],
    ffmpeg_policy: Mapping[str, Any],
) -> dict[str, Any]:
    lowered = [name.lower() for name in names]
    gpl_markers = [
        marker
        for marker in ffmpeg_policy.get("gpl_binary_markers", [])
        if any(marker.lower() in name for name in lowered)
    ]
    version3_markers = [
        marker
        for marker in ffmpeg_policy.get("version3_binary_markers", [])
        if any(marker.lower() in name for name in lowered)
    ]
    nonfree_markers = [
        marker
        for marker in ffmpeg_policy.get("nonfree_binary_markers", [])
        if any(marker.lower() in name for name in lowered)
    ]
    return {
        "gpl_markers_found": sorted(gpl_markers),
        "version3_markers_found": sorted(version3_markers),
        "nonfree_markers_found": sorted(nonfree_markers),
        "effective_ffmpeg_license": (
            ffmpeg_policy.get("gpl_effective_license")
            if gpl_markers
            else "LGPL-2.1-or-later-or-unverified"
        ),
    }


def collect_ffmpeg_evidence(
    ffmpeg_policy: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    findings: list[str] = []
    warnings: list[str] = []
    av_distributions = [
        distribution
        for distribution in metadata.distributions()
        if canonicalize_name(distribution.metadata.get("Name", "")) == "av"
    ]
    binaries: dict[str, dict[str, Any]] = {}
    for distribution in av_distributions:
        for relative in distribution.files or []:
            normalized = str(relative).replace("\\", "/")
            if "av.libs/" not in normalized:
                continue
            path = Path(distribution.locate_file(relative))
            if not path.is_file():
                findings.append(
                    f"PyAV RECORD binary is missing: {Path(normalized).name}"
                )
                continue
            name = path.name
            binaries[name] = {
                "name": name,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }

    try:
        import av
    except ImportError:
        findings.append("PyAV cannot be imported")
        library_versions: dict[str, list[int]] = {}
        av_version = None
    else:
        av_version = av.__version__
        library_versions = {
            name: list(value)
            for name, value in sorted(av.library_versions.items())
        }

    expected_av = ffmpeg_policy.get("pyav_version")
    if av_version != expected_av:
        findings.append(
            f"PyAV version {av_version!r} does not match {expected_av!r}"
        )
    expected_versions = ffmpeg_policy.get("expected_library_versions", {})
    if library_versions != expected_versions:
        findings.append("linked FFmpeg library versions do not match policy")
    if not binaries:
        findings.append("PyAV wheel exposes no bundled av.libs binaries")

    binary_analysis = analyze_binary_names(
        sorted(binaries),
        ffmpeg_policy,
    )
    expected_gpl = sorted(ffmpeg_policy.get("gpl_binary_markers", []))
    if binary_analysis["gpl_markers_found"] != expected_gpl:
        findings.append("PyAV GPL binary marker set does not match policy")
    expected_version3 = sorted(
        ffmpeg_policy.get("version3_binary_markers", [])
    )
    if binary_analysis["version3_markers_found"] != expected_version3:
        findings.append("PyAV version-3 binary marker set does not match policy")
    if binary_analysis["nonfree_markers_found"]:
        findings.append(
            "PyAV wheel contains nonfree markers: "
            f"{binary_analysis['nonfree_markers_found']}"
        )
    if binary_analysis["gpl_markers_found"]:
        warnings.append(
            "PyAV bundles GPL-triggering FFmpeg components; never attach this "
            "runtime or its binaries to a source-only project release"
        )

    evidence = {
        "pyav_version": av_version,
        "linked_library_versions": library_versions,
        "bundled_binaries": [binaries[name] for name in sorted(binaries)],
        **binary_analysis,
        "bundled_runtime_allowed": ffmpeg_policy.get(
            "bundled_runtime_allowed"
        ),
        "official_legal_url": ffmpeg_policy.get("official_legal_url"),
        "official_license_url": ffmpeg_policy.get("official_license_url"),
        "pyav_binary_build_source": ffmpeg_policy.get(
            "pyav_binary_build_source"
        ),
    }
    return evidence, findings, warnings


def _git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def collect_repository_evidence(
    root: Path,
    forbidden_suffixes: Sequence[str],
) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    commit = _git_output(root, "rev-parse", "HEAD")
    status = _git_output(root, "status", "--short")
    tracked = _git_output(root, "ls-files").splitlines()
    forbidden = sorted(
        path
        for path in tracked
        if Path(path).suffix.lower() in set(forbidden_suffixes)
    )
    if forbidden:
        findings.append(f"forbidden runtime binaries are tracked: {forbidden}")
    return {
        "commit": commit,
        "dirty": bool(status),
        "tracked_file_count": len(tracked),
        "forbidden_runtime_files": forbidden,
    }, findings


def collect_model_evidence(
    model_policy: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    from openmultimodal_lab.adapters.qwen3_vl import (
        DEFAULT_MODEL_ID as QWEN_MODEL_ID,
    )
    from openmultimodal_lab.adapters.qwen3_vl import (
        DEFAULT_MODEL_REVISION as QWEN_REVISION,
    )
    from openmultimodal_lab.adapters.smolvlm2 import (
        DEFAULT_MODEL_ID as SMOL_MODEL_ID,
    )
    from openmultimodal_lab.adapters.smolvlm2 import (
        DEFAULT_MODEL_REVISION as SMOL_REVISION,
    )

    actual = [
        {"model_id": QWEN_MODEL_ID, "revision": QWEN_REVISION},
        {"model_id": SMOL_MODEL_ID, "revision": SMOL_REVISION},
    ]
    expected_by_id = {
        value.get("model_id"): dict(value) for value in model_policy
    }
    findings: list[str] = []
    evidence: list[dict[str, Any]] = []
    for item in actual:
        expected = expected_by_id.get(item["model_id"])
        if expected is None:
            findings.append(
                f"model {item['model_id']} is missing from license policy"
            )
            continue
        if item["revision"] != expected.get("revision"):
            findings.append(
                f"model {item['model_id']} revision differs from policy"
            )
        if not re.fullmatch(r"[0-9a-f]{40}", item["revision"]):
            findings.append(
                f"model {item['model_id']} revision is not immutable"
            )
        evidence.append(expected)
    if len(evidence) != len(model_policy):
        findings.append("model policy and adapter model sets differ")
    return sorted(evidence, key=lambda value: value["model_id"]), findings


def _write_constraints(path: Path, packages: Sequence[dict[str, Any]]) -> None:
    lines: list[str] = []
    for package in packages:
        if package["name"] == "openmultimodal-lab":
            continue
        if len(package["versions"]) != 1:
            continue
        lines.append(f"{package['name']}=={package['versions'][0]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _snapshot_hash(snapshot: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def build_audit(
    policy: Mapping[str, Any],
    repository_root: Path,
    *,
    require_clean: bool,
) -> dict[str, Any]:
    findings: list[str] = []
    warnings: list[str] = []
    packages = collect_installed_packages()
    findings.extend(audit_packages(packages, policy))
    weak_copyleft_packages = sorted(
        package["name"]
        for package in packages
        if any(
            classification["tier"] == "weak-copyleft"
            for classification in package.get("license_classifications", [])
        )
    )
    if weak_copyleft_packages:
        warnings.append(
            "weak-copyleft package metadata requires source-only notice "
            f"review: {weak_copyleft_packages}"
        )

    python_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    if python_minor not in policy.get("python_minors", []):
        findings.append(f"Python {python_minor} is outside the audited policy")

    ffmpeg, ffmpeg_findings, ffmpeg_warnings = collect_ffmpeg_evidence(
        policy.get("ffmpeg", {})
    )
    findings.extend(ffmpeg_findings)
    warnings.extend(ffmpeg_warnings)
    models, model_findings = collect_model_evidence(policy.get("models", []))
    findings.extend(model_findings)
    repository, repository_findings = collect_repository_evidence(
        repository_root,
        policy.get("forbidden_tracked_suffixes", []),
    )
    findings.extend(repository_findings)
    if require_clean and repository["dirty"]:
        findings.append("repository is dirty during a required-clean audit")

    snapshot: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "PASS" if not findings else "FAIL",
        "distribution_scope": policy.get("distribution_scope"),
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "repository": repository,
        "packages": packages,
        "models": models,
        "ffmpeg": ffmpeg,
        "findings": sorted(findings),
        "warnings": sorted(warnings),
    }
    snapshot["snapshot_sha256"] = _snapshot_hash(snapshot)
    return snapshot


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--policy",
        type=Path,
        default=project_root / "docs" / "license-audit-policy.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--constraints-output", type=Path)
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--validate-policy-only", action="store_true")
    args = parser.parse_args()

    try:
        policy = _bounded_json(args.policy)
        policy_findings = validate_policy(policy)
        if policy_findings:
            for finding in policy_findings:
                print(f"[FAIL] {finding}")
            print(
                f"License audit policy FAIL: "
                f"{len(policy_findings)} finding(s)"
            )
            return 1
        if args.validate_policy_only:
            print("License audit policy PASS")
            return 0
        if args.output is None:
            parser.error("--output is required unless --validate-policy-only is used")
        snapshot = build_audit(
            policy,
            project_root,
            require_clean=args.require_clean,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"License audit could not run: {type(exc).__name__}: {exc}")
        return 2

    if args.output is None:  # Guard remains active under optimized Python.
        print("License audit could not run: output path is missing")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if args.constraints_output is not None:
        _write_constraints(args.constraints_output, snapshot["packages"])

    print(
        f"License audit {snapshot['status']}: "
        f"{len(snapshot['packages'])} packages, "
        f"{len(snapshot['ffmpeg']['bundled_binaries'])} PyAV binaries, "
        f"{len(snapshot['findings'])} finding(s), "
        f"{len(snapshot['warnings'])} warning(s)"
    )
    for finding in snapshot["findings"]:
        print(f"[FAIL] {finding}")
    for warning in snapshot["warnings"]:
        print(f"[WARN] {warning}")
    print(f"Snapshot SHA-256: {snapshot['snapshot_sha256']}")
    return 0 if snapshot["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

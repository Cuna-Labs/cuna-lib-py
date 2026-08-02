"""Verify the immutable PRD-094 handoff before any release-stage identity request."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from _evidence_utils import canonical_json_sha256, file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import canonical_json_sha256, file_sha256


def _manifest(root: Path, name: str) -> dict[str, object] | None:
    manifests = list(root.rglob(name))
    if len(manifests) != 1:
        return None
    value = json.loads(manifests[0].read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def _validate_core(root: Path, source: str, manifest: dict[str, object]) -> str | None:
    if re.fullmatch(r"[0-9a-f]{40}", source) is None:
        return "immutable-source-invalid"
    if manifest.get("source") != source:
        return "manifest-source-mismatch"
    artifacts = sorted(
        (
            {"filename": path.name, "sha256": file_sha256(path)}
            for path in root.rglob("runa_sdk-*")
            if path.suffix == ".whl" or path.name.endswith(".tar.gz")
        ),
        key=lambda item: item["filename"],
    )
    if len(artifacts) != 2 or manifest.get("artifacts") != artifacts:
        return "artifact-substitution"
    if len(manifest.get("cells", [])) != 10 or len(manifest.get("performanceCells", [])) != 20:
        return "matrix-evidence-incomplete"
    return None


def validate_candidate_handoff(root: Path, source: str) -> str | None:
    manifest = _manifest(root, "candidate-manifest.json")
    if manifest is None:
        return "candidate-manifest-missing"
    core = _validate_core(root, source, manifest)
    if core is not None:
        return core
    if (
        manifest.get("verdict") != "candidate-pass"
        or manifest.get("releaseEligible") is not False
        or any(str(key).startswith("inheritedEvidence") for key in manifest)
    ):
        return "candidate-manifest-overclaim"
    return None


def _validate_inherited_manifest(
    root: Path, source: str, name: str, verdict: str, release_eligible: bool
) -> str | None:
    manifest = _manifest(root, name)
    if manifest is None:
        return "admission-manifest-missing"
    core = _validate_core(root, source, manifest)
    if core is not None:
        return core
    if (
        manifest.get("verdict") != verdict
        or manifest.get("releaseEligible") is not release_eligible
    ):
        return "admission-manifest-mismatch"
    inherited = manifest.get("inheritedEvidence")
    required = {
        "prd013Security",
        "prd014Compatibility",
        "prd015Conformance",
        "prd016Quality",
        "prd017Budgets",
        "releaseManifest",
        "sbom",
        "provenance",
    }
    if not isinstance(inherited, dict) or set(inherited) != required:
        return "inherited-supply-chain-evidence-missing"
    if any(
        not isinstance(value, dict)
        or value.get("verdict") != "pass"
        or not isinstance(value.get("files"), list)
        or not value["files"]
        for value in inherited.values()
    ):
        return "inherited-supply-chain-evidence-blocked"
    for digest_name in (
        "inheritedEvidenceBundleSha256",
        "inheritedEvidenceStatementSha256",
    ):
        if re.fullmatch(r"[0-9a-f]{64}", str(manifest.get(digest_name, ""))) is None:
            return "inherited-supply-chain-evidence-unbound"
    return None


def validate_release_core_handoff(root: Path, source: str) -> str | None:
    return _validate_inherited_manifest(
        root, source, "release-core-manifest.json", "core-pass", False
    )


def validate_handoff(root: Path, source: str) -> str | None:
    core_error = validate_release_core_handoff(root, source)
    if core_error is not None:
        return core_error
    core_paths = list(root.rglob("release-core-manifest.json"))
    envelope = _manifest(root, "release-admission-manifest.json")
    if len(core_paths) != 1 or envelope is None:
        return "admission-envelope-missing"
    core = json.loads(core_paths[0].read_text(encoding="utf-8"))
    receipt = envelope.get("approvalReceipt")
    if (
        set(envelope) != {"approvalReceipt", "core", "coreDigest", "schemaVersion", "state"}
        or envelope.get("schemaVersion") != 1
        or envelope.get("state") != "admitted"
        or envelope.get("coreDigest") != canonical_json_sha256(core)
        or envelope.get("core")
        != {"path": "release-core-manifest.json", "sha256": file_sha256(core_paths[0])}
        or not isinstance(receipt, dict)
        or set(receipt) != {"receiptId", "receiptSha256", "verifier"}
        or not all(isinstance(receipt.get(key), str) and receipt[key] for key in receipt)
    ):
        return "admission-envelope-binding-invalid"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--core", action="store_true")
    args = parser.parse_args()
    if args.candidate and args.core:
        raise SystemExit("handoff-mode-ambiguous")
    category = (
        validate_candidate_handoff(args.handoff, args.source)
        if args.candidate
        else validate_release_core_handoff(args.handoff, args.source)
        if args.core
        else validate_handoff(args.handoff, args.source)
    )
    if category is not None:
        print(
            json.dumps(
                {"category": category, "requirement": "R-095-08", "verdict": "blocked"},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print('{"requirement":"R-095-08","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

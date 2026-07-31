"""Verify the immutable PRD-094 handoff before any release-stage identity request."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256


def validate_handoff(root: Path, source: str) -> str | None:
    if re.fullmatch(r"[0-9a-f]{40}", source) is None:
        return "immutable-source-invalid"
    manifests = list(root.rglob("admission-manifest.json"))
    if len(manifests) != 1:
        return "admission-manifest-missing"
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    if manifest.get("verdict") != "pass" or manifest.get("source") != source:
        return "admission-manifest-mismatch"
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    category = validate_handoff(args.handoff, args.source)
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

"""Verify the externally accepted and signed 20-cell performance baseline set."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from _evidence_utils import file_sha256
    from _release_identity import (
        CUNA_SDK_REPOSITORY,
        GITHUB_OIDC_ISSUER,
        PERFORMANCE_EVIDENCE_IDENTITIES,
        signer_repository_is_expected,
    )
    from inherited_evidence_gate import verify_sigstore
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256
    from tools._release_identity import (
        CUNA_SDK_REPOSITORY,
        GITHUB_OIDC_ISSUER,
        PERFORMANCE_EVIDENCE_IDENTITIES,
        signer_repository_is_expected,
    )
    from tools.inherited_evidence_gate import verify_sigstore

# The run declares which repository's signature it will accept, before it reads a
# single byte of the baseline set. The set under verification never selects it.
DEFAULT_EXPECTED_REPOSITORY = CUNA_SDK_REPOSITORY
ACCEPTED_SIGNER_REPOSITORIES = frozenset(PERFORMANCE_EVIDENCE_IDENTITIES.values())


def validate_baselines(
    root: Path, *, expected_repository: str = DEFAULT_EXPECTED_REPOSITORY
) -> str | None:
    if expected_repository not in ACCEPTED_SIGNER_REPOSITORIES:
        return "baseline-expected-repository-unknown"
    index_path = root / "baseline-index.json"
    bundle = root / "baseline-index.sigstore.json"
    if not index_path.is_file() or not bundle.is_file():
        return "signed-baseline-index-missing"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "baseline-index-invalid"
    source = index.get("source")
    if not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{40}", source) is None:
        return "baseline-source-invalid"
    entries = index.get("baselines")
    if not isinstance(entries, list) or len(entries) != 20:
        return "baseline-matrix-incomplete"
    expected = {
        f"baseline-{python}-{form}-{mode}.json"
        for python in ("3.10", "3.11", "3.12", "3.13", "3.14")
        for form in ("wheel", "sdist")
        for mode in ("sync", "async")
    }
    observed: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            return "baseline-index-invalid"
        name = entry["path"]
        if name not in expected:
            return "baseline-cell-invalid"
        path = root / name
        if not path.is_file() or entry.get("sha256") != file_sha256(path):
            return "baseline-digest-mismatch"
        baseline = json.loads(path.read_text(encoding="utf-8"))
        authority = baseline.get("authority")
        identity = authority.get("certificateIdentity") if isinstance(authority, dict) else None
        if (
            baseline.get("status") != "accepted"
            or not baseline.get("approvalReference")
            or not isinstance(baseline.get("metrics"), dict)
            or not isinstance(identity, str)
            or identity not in PERFORMANCE_EVIDENCE_IDENTITIES
            or authority.get("issuer") != GITHUB_OIDC_ISSUER
        ):
            return "baseline-not-accepted"
        if not signer_repository_is_expected(
            identity, PERFORMANCE_EVIDENCE_IDENTITIES, expected_repository
        ):
            return "baseline-authority-unexpected"
        observed.add(name)
    if observed != expected:
        return "baseline-matrix-incomplete"
    if not verify_sigstore(
        index_path,
        bundle,
        source,
        workflow_name="performance-baseline.yml",
        repository=expected_repository,
    ):
        return "baseline-signature-invalid"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--expected-repository",
        default=DEFAULT_EXPECTED_REPOSITORY,
        choices=sorted(ACCEPTED_SIGNER_REPOSITORIES),
        help=(
            "repository whose performance-baseline signature this run accepts; "
            "historical evidence is verified by naming its repository here"
        ),
    )
    args = parser.parse_args()
    category = validate_baselines(args.root, expected_repository=args.expected_repository)
    if category is not None:
        print(json.dumps({"category": category, "verdict": "blocked"}, sort_keys=True))
        return 1
    print('{"requirement":"R-017-21","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail-closed release admission for the fixed Python release identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import tomllib

EXPECTED_REPOSITORY = "Runa-Laboratories/runa-lib-py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blocked(requirement: str, category: str) -> int:
    print(
        json.dumps(
            {"category": category, "requirement": requirement, "verdict": "blocked"},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("dist"))
    parser.add_argument(
        "--evidence", type=Path, default=Path(".runa/external-release-evidence.json")
    )
    parser.add_argument(
        "--bundle", type=Path, default=Path(".runa/external-release-evidence.sigstore.json")
    )
    args = parser.parse_args()
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    if policy["sourceControl"]["repository"] != EXPECTED_REPOSITORY:
        return blocked("R-095-01", "safe-policy-mismatch")
    if re.fullmatch(r"py-v\d+\.\d+\.\d+", args.tag) is None:
        return blocked("R-095-01", "safe-tag-shape-mismatch")
    if args.tag != f"py-v{version}":
        return blocked("R-095-02", "safe-tag-version-mismatch")
    if not args.evidence.is_file():
        return blocked("R-095-10", "external-evidence-missing")
    if not args.bundle.is_file():
        return blocked("R-095-10", "signed-evidence-bundle-missing")
    source_commit_hint = os.environ.get("GITHUB_SHA")
    if source_commit_hint is None or re.fullmatch(r"[0-9a-f]{40}", source_commit_hint) is None:
        return blocked("R-095-01", "immutable-source-identity-missing")
    verification = subprocess.run(  # noqa: S603 - fixed interpreter and pinned verifier
        [
            sys.executable,
            "-m",
            "sigstore",
            "verify",
            "github",
            "--offline",
            "--bundle",
            str(args.bundle),
            "--cert-identity",
            policy["tag"]["signature"]["certificateIdentity"],
            "--repository",
            EXPECTED_REPOSITORY,
            "--sha",
            source_commit_hint,
            "--name",
            "release.yml",
            "--ref",
            f"refs/tags/{args.tag}",
            str(args.evidence),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if verification.returncode != 0:
        return blocked("R-095-01", "sigstore-verification-failed")
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    source_commit = os.environ.get("GITHUB_SHA", evidence.get("sourceCommit"))
    if (
        not isinstance(source_commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None
        or evidence.get("sourceCommit") != source_commit
        or evidence.get("tag") != args.tag
        or evidence.get("tagVerified") is not True
    ):
        return blocked("R-095-01", "source-or-tag-evidence-mismatch")
    policy_digest = hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if evidence.get("policySha256") != policy_digest:
        return blocked("R-095-01", "policy-digest-mismatch")
    branch_policy = policy["sourceControl"]["branchProtection"]
    if evidence.get("branchProtection") != branch_policy:
        return blocked("R-095-01", "branch-protection-mismatch")
    checks = evidence.get("statusChecks")
    if not isinstance(checks, dict) or any(
        checks.get(name) != {"commit": source_commit, "verdict": "pass"}
        for name in branch_policy["requiredStatusChecks"]
    ):
        return blocked("R-095-08", "required-status-evidence-mismatch")
    trusted = policy["trustedPublisher"]
    if evidence.get("trustedPublisher") != trusted:
        return blocked("R-095-10", "trusted-publisher-record-mismatch")
    identity = evidence.get("identity")
    identity_fields = (
        "issuer",
        "subject",
        "audience",
        "repository",
        "workflow",
        "environment",
    )
    if not isinstance(identity, dict) or any(
        identity.get(name) != trusted[name] for name in identity_fields
    ):
        return blocked("R-095-11", "workload-identity-mismatch")
    try:
        expires = datetime.fromisoformat(str(identity["expiresAt"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return blocked("R-095-11", "workload-identity-expiry-invalid")
    if expires <= datetime.now(timezone.utc):
        return blocked("R-095-11", "workload-identity-expired")
    approvals = evidence.get("approvals")
    if (
        not isinstance(approvals, list)
        or not approvals
        or any(
            not isinstance(item, dict)
            or item.get("commit") != source_commit
            or not isinstance(item.get("reference"), str)
            or item.get("role") not in {"release-owner", "security-owner"}
            for item in approvals
        )
        or not any(item.get("role") == "release-owner" for item in approvals)
    ):
        return blocked("R-095-08", "approval-evidence-missing")
    candidates = sorted(args.artifacts.glob("runa_sdk-*"))
    observed = [
        {"filename": path.name, "sha256": digest(path)}
        for path in candidates
        if path.suffix == ".whl" or path.name.endswith(".tar.gz")
    ]
    if len(observed) != 2 or evidence.get("artifacts") != observed:
        return blocked("R-095-03", "artifact-evidence-mismatch")
    print('{"requirement":"R-095-01","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

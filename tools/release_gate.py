"""Fail-closed release admission for the fixed Python release identity."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

try:
    from _approval import github_environment_execution, verify_provider_receipt
    from _evidence_utils import canonical_json_sha256, file_sha256
    from _release_identity import CUNA_SDK_REPOSITORY
    from build_external_release_evidence import (
        python_release_core_binding,
        release_manifest_binding,
    )
    from sbom_gate import validate_configuration
except ModuleNotFoundError:
    from tools._approval import github_environment_execution, verify_provider_receipt
    from tools._evidence_utils import canonical_json_sha256, file_sha256
    from tools._release_identity import CUNA_SDK_REPOSITORY
    from tools.build_external_release_evidence import (
        python_release_core_binding,
        release_manifest_binding,
    )
    from tools.sbom_gate import validate_configuration

EXPECTED_REPOSITORY = CUNA_SDK_REPOSITORY


def policy_reachability(policy: object, current_check: str = "release-admission") -> bool:
    """Reject circular check dependencies and an identity bound to the wrong ref."""

    if not isinstance(policy, dict):
        return False
    try:
        checks = policy["sourceControl"]["preAdmissionStatusChecks"]
        protected_checks = policy["sourceControl"]["branchProtection"]["requiredStatusChecks"]
        identity = policy["tag"]["signature"]["certificateIdentity"]
    except (KeyError, TypeError):
        return False
    return (
        isinstance(checks, list)
        and bool(checks)
        and current_check not in checks
        and isinstance(protected_checks, list)
        and current_check in protected_checks
        and isinstance(identity, str)
        and identity.endswith("@refs/heads/main")
    )


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
    parser.add_argument("--approval-receipt", type=Path, default=Path("approval-receipt.json"))
    parser.add_argument("--approval-signature", type=Path, default=Path("approval-receipt.sig"))
    parser.add_argument("--approval-trust", type=Path, default=Path(".runa/approval-trust.json"))
    parser.add_argument("--admission-output", type=Path)
    args = parser.parse_args()
    policy = json.loads(Path(".runa/release-policy.json").read_text(encoding="utf-8"))
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    if not policy_reachability(policy):
        return blocked("R-095-08", "release-policy-unreachable")
    try:
        supply_chain_tools = json.loads(
            Path(".runa/supply-chain-tools.json").read_text(encoding="utf-8")
        )
        validate_configuration(policy, supply_chain_tools)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return blocked("R-018-10", "sbom-policy-or-schema-invalid")
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
    git = shutil.which("git")
    if git is None:
        return blocked("R-095-01", "git-verifier-missing")
    tag_target = subprocess.run(  # noqa: S603
        [git, "rev-list", "-n", "1", args.tag],
        capture_output=True,
        text=True,
        check=False,
    )
    if tag_target.returncode != 0 or tag_target.stdout.strip() != source_commit_hint:
        return blocked("R-095-01", "tag-commit-mismatch")
    gitsign = shutil.which("gitsign")
    if gitsign is None:
        return blocked("R-095-01", "sigstore-tag-verifier-missing")
    tag_verification = subprocess.run(  # noqa: S603
        [
            gitsign,
            "verify",
            "--certificate-identity",
            policy["tag"]["signature"]["certificateIdentity"],
            "--certificate-oidc-issuer",
            policy["tag"]["signature"]["issuer"],
            args.tag,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if tag_verification.returncode != 0:
        return blocked("R-095-01", "sigstore-tag-verification-failed")
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
            policy["evidence"]["signature"]["certificateIdentity"],
            "--repository",
            EXPECTED_REPOSITORY,
            "--sha",
            source_commit_hint,
            "--name",
            "release-evidence.yml",
            "--ref",
            "refs/heads/main",
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
    ):
        return blocked("R-095-01", "source-or-tag-evidence-mismatch")
    policy_digest = canonical_json_sha256(policy)
    if evidence.get("policySha256") != policy_digest:
        return blocked("R-095-01", "policy-digest-mismatch")
    admission_run = evidence.get("admissionRun")
    if (
        not isinstance(admission_run, dict)
        or re.fullmatch(r"[1-9][0-9]*", str(admission_run.get("runId", ""))) is None
        or admission_run.get("headSha") != source_commit
        or admission_run.get("conclusion") != "success"
        or admission_run.get("workflow") != "py-quality-gates"
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
    environment_gate = evidence.get("environmentGateEvidence")
    if (
        not isinstance(environment_gate, dict)
        or environment_gate.get("commit") != source_commit
        or environment_gate.get("type") != "github-environment-gate"
        or not isinstance(environment_gate.get("reference"), str)
    ):
        return blocked("R-095-08", "environment-gate-evidence-missing")
    try:
        execution_authority = github_environment_execution(
            environment_gate["reference"], str(trusted["environment"])
        )
    except ValueError:
        return blocked("R-095-08", "environment-gate-evidence-invalid")
    if environment_gate.get("executionAuthority") != execution_authority:
        return blocked("R-095-08", "environment-gate-evidence-invalid")
    protection = environment_gate.get("environmentProtection")
    if not isinstance(protection, dict):
        return blocked("R-095-08", "environment-gate-evidence-invalid")
    protection_path = args.evidence.parent / str(protection.get("path", ""))
    try:
        protection_value = json.loads(protection_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return blocked("R-095-08", "environment-gate-evidence-invalid")
    if (
        protection.get("sha256") != file_sha256(protection_path)
        or protection_value
        != {
            "environment": trusted["environment"],
            "requiredReviewerCount": protection.get("requiredReviewerCount"),
        }
        or type(protection.get("requiredReviewerCount")) is not int
        or protection["requiredReviewerCount"] < 1
    ):
        return blocked("R-095-08", "environment-gate-evidence-invalid")
    release_manifest = evidence.get("releaseManifest")
    try:
        expected_release_manifest = release_manifest_binding(args.artifacts)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return blocked("R-095-08", "release-manifest-binding-invalid")
    if release_manifest != expected_release_manifest:
        return blocked("R-095-08", "release-manifest-binding-missing")
    try:
        release_core = python_release_core_binding(args.artifacts)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return blocked("R-095-08", "release-core-manifest-invalid")
    if evidence.get("releaseCore") != release_core:
        return blocked("R-095-08", "release-core-binding-missing")
    candidates = sorted(args.artifacts.rglob("runa_sdk-*"))
    observed = [
        {"filename": path.name, "sha256": file_sha256(path)}
        for path in candidates
        if path.suffix == ".whl" or path.name.endswith(".tar.gz")
    ]
    if len(observed) != 2 or evidence.get("artifacts") != observed:
        return blocked("R-095-03", "artifact-evidence-mismatch")
    core_digest = release_core["coreDigest"]
    try:
        receipt = verify_provider_receipt(
            args.approval_receipt,
            args.approval_signature,
            args.approval_trust,
            core_digest=core_digest,
            artifacts=observed,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return blocked("R-095-08", str(error))
    if evidence.get("approvalReceipt") != {**receipt, "verdict": "pass"}:
        return blocked("R-095-08", "approval-envelope-binding-invalid")
    if args.admission_output is not None:
        final_admission = {
            "approvalReceipt": receipt,
            "core": {
                "path": release_core["path"],
                "sha256": release_core["sha256"],
            },
            "coreDigest": core_digest,
            "schemaVersion": 1,
            "state": "admitted",
        }
        args.admission_output.write_text(
            json.dumps(final_admission, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print('{"requirement":"R-095-08","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

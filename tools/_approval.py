"""Validate GitHub Environment approval identities supplied by trusted workflows."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

try:
    from _evidence_utils import file_sha256
    from _release_identity import CUNA_AUTHORITY_REPOSITORY, LEGACY_AUTHORITY_REPOSITORY
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256
    from tools._release_identity import CUNA_AUTHORITY_REPOSITORY, LEGACY_AUTHORITY_REPOSITORY

LEGACY_RECEIPT_RETRIEVAL_PREFIX = (
    f"https://github.com/{LEGACY_AUTHORITY_REPOSITORY}/releases/download"
)
CUNA_RECEIPT_RETRIEVAL_PREFIX = f"https://github.com/{CUNA_AUTHORITY_REPOSITORY}/releases/download"
CUNA_APPROVAL_AUTHORITY = {
    "approverRole": "cuna-release-authority",
    "artifactName": "cuna-python-release-approval",
    "event": "workflow_dispatch",
    "maximumValiditySeconds": 86_400,
    "policyId": "cuna-python-release-v1",
    "providerId": "cuna-release-authority-v1",
    "ref": "main",
    "repository": CUNA_AUTHORITY_REPOSITORY,
    "retrievalUriPrefix": CUNA_RECEIPT_RETRIEVAL_PREFIX,
    "workflow": ".github/workflows/release-authority.yml",
}

_REFERENCE = re.compile(
    r"^github-environment://repositories/(?P<repository_id>[1-9][0-9]*)/"
    r"environments/(?P<environment>[a-z0-9][a-z0-9-]{0,62})/"
    r"runs/(?P<run_id>[1-9][0-9]*)/attempts/(?P<attempt>[1-9][0-9]*)/"
    r"actors/(?P<actor_id>[1-9][0-9]*)$"
)


def github_environment_execution(reference: str, expected_environment: str) -> dict[str, str]:
    """Return normalized execution identity; this is not an approval receipt."""

    match = _REFERENCE.fullmatch(reference)
    if match is None or match.group("environment") != expected_environment:
        raise ValueError("github-environment-execution-invalid")
    return {
        "attempt": match.group("attempt"),
        "environment": match.group("environment"),
        "executionActorId": match.group("actor_id"),
        "repositoryId": match.group("repository_id"),
        "runId": match.group("run_id"),
        "type": "github-environment-execution",
    }


def environment_gate_evidence(path: Path, expected_environment: str) -> dict[str, object]:
    """Bind an externally observed required-reviewer rule without retaining identities."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("environment-gate-evidence-invalid") from None
    if (
        not isinstance(value, dict)
        or set(value) != {"environment", "requiredReviewerCount"}
        or value.get("environment") != expected_environment
        or type(value.get("requiredReviewerCount")) is not int
        or value["requiredReviewerCount"] < 1
    ):
        raise ValueError("environment-gate-evidence-invalid")
    return {
        "environment": expected_environment,
        "path": path.name,
        "requiredReviewerCount": value["requiredReviewerCount"],
        "sha256": file_sha256(path),
    }


# Backwards-compatible names for the performance-baseline workflow. Release admission
# deliberately uses the non-approval names above and never treats these facts as approval.
external_environment_approval = github_environment_execution
environment_protection_evidence = environment_gate_evidence


def verify_provider_receipt(
    receipt_path: Path,
    signature_path: Path,
    trust_path: Path,
    *,
    core_digest: str,
    artifacts: list[dict[str, str]],
    now: datetime | None = None,
) -> dict[str, str]:
    """Verify a detached provider receipt against a separately accepted trust root."""

    trust = json.loads(trust_path.read_text(encoding="utf-8"))
    authority = trust.get("authority") if isinstance(trust, dict) else None
    schema_version = trust.get("schemaVersion") if isinstance(trust, dict) else None
    legacy_prefixes = (
        trust.get("legacyReceiptRetrievalUriPrefixes", []) if isinstance(trust, dict) else []
    )
    if (
        schema_version not in {1, 2}
        or trust.get("status") != "accepted"
        or not isinstance(authority, dict)
        or set(trust)
        != (
            {"authority", "schemaVersion", "status"}
            if schema_version == 1
            else {
                "authority",
                "legacyReceiptRetrievalUriPrefixes",
                "schemaVersion",
                "status",
            }
        )
        or not isinstance(legacy_prefixes, list)
        or (schema_version == 2 and legacy_prefixes != [LEGACY_RECEIPT_RETRIEVAL_PREFIX])
        or any(
            not isinstance(prefix, str)
            or re.fullmatch(
                r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/releases/download",
                prefix,
            )
            is None
            for prefix in legacy_prefixes
        )
    ):
        raise ValueError("approval-trust-root-unconfigured")
    required_authority = {
        "approverRole",
        "artifactName",
        "event",
        "maximumValiditySeconds",
        "policyId",
        "providerId",
        "publicKeyPath",
        "publicKeySha256",
        "repository",
        "ref",
        "retrievalUriPrefix",
        "workflow",
    }
    if set(authority) != required_authority:
        raise ValueError("approval-trust-root-invalid")
    public_key_path = trust_path.parent / str(authority["publicKeyPath"])
    if (
        not public_key_path.is_file()
        or file_sha256(public_key_path) != authority["publicKeySha256"]
        or any(
            authority.get(field) != expected for field, expected in CUNA_APPROVAL_AUTHORITY.items()
        )
    ):
        raise ValueError("approval-trust-root-invalid")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    required_receipt = {
        "approverRole",
        "artifacts",
        "coreDigest",
        "decision",
        "expiresAt",
        "issuedAt",
        "policyId",
        "providerId",
        "receiptId",
        "retrievalUri",
        "revoked",
        "schemaVersion",
    }
    expected_artifacts = sorted(artifacts, key=lambda item: item["filename"])
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required_receipt
        or receipt.get("schemaVersion") != 1
        or receipt.get("decision") != "approve"
        or receipt.get("revoked") is not False
        or receipt.get("approverRole") != authority["approverRole"]
        or receipt.get("policyId") != authority["policyId"]
        or receipt.get("providerId") != authority["providerId"]
        or receipt.get("coreDigest") != core_digest
        or receipt.get("artifacts") != expected_artifacts
        # The legacy prefix is retained only so immutable historical receipts remain
        # discoverable. It is never an admission path for a newly verified receipt.
        or not str(receipt.get("retrievalUri", "")).startswith(
            str(authority["retrievalUriPrefix"]).rstrip("/") + "/"
        )
        or re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", str(receipt.get("receiptId", ""))) is None
    ):
        raise ValueError("approval-receipt-binding-invalid")
    try:
        issued = datetime.fromisoformat(str(receipt["issuedAt"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(receipt["expiresAt"]).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("approval-receipt-time-invalid") from None
    observed_now = now or datetime.now(timezone.utc)
    maximum_validity = authority["maximumValiditySeconds"]
    if (
        type(maximum_validity) is not int
        or maximum_validity <= 0
        or issued > observed_now
        or expires <= observed_now
        or expires <= issued
        or (expires - issued).total_seconds() > maximum_validity
    ):
        raise ValueError("approval-receipt-time-invalid")
    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        signature = base64.b64decode(signature_path.read_text(encoding="ascii"), validate=True)
        loaded = serialization.load_pem_public_key(public_key_path.read_bytes())
        if not isinstance(loaded, Ed25519PublicKey):
            raise ValueError("approval-trust-root-invalid")
        loaded.verify(signature, encoded)
    except (InvalidSignature, ValueError, OSError, UnicodeError):
        raise ValueError("approval-receipt-signature-invalid") from None
    return {
        "receiptId": receipt["receiptId"],
        "receiptSha256": file_sha256(receipt_path),
        "verifier": "ed25519-detached-v1",
    }

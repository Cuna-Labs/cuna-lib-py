"""Validate GitHub Environment approval identities supplied by trusted workflows."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from _evidence_utils import file_sha256
except ModuleNotFoundError:
    from tools._evidence_utils import file_sha256

_REFERENCE = re.compile(
    r"^github-environment://repositories/(?P<repository_id>[1-9][0-9]*)/"
    r"environments/(?P<environment>[a-z0-9][a-z0-9-]{0,62})/"
    r"runs/(?P<run_id>[1-9][0-9]*)/attempts/(?P<attempt>[1-9][0-9]*)/"
    r"actors/(?P<actor_id>[1-9][0-9]*)$"
)


def external_environment_approval(reference: str, expected_environment: str) -> dict[str, str]:
    """Return normalized external identity or fail closed on a self-asserted label."""

    match = _REFERENCE.fullmatch(reference)
    if match is None or match.group("environment") != expected_environment:
        raise ValueError("external-environment-approval-invalid")
    return {
        "attempt": match.group("attempt"),
        "environment": match.group("environment"),
        "executionActorId": match.group("actor_id"),
        "repositoryId": match.group("repository_id"),
        "runId": match.group("run_id"),
        "type": "github-environment-execution",
    }


def environment_protection_evidence(path: Path, expected_environment: str) -> dict[str, object]:
    """Bind an externally observed required-reviewer rule without retaining identities."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("environment-protection-evidence-invalid") from None
    if (
        not isinstance(value, dict)
        or set(value) != {"environment", "requiredReviewerCount"}
        or value.get("environment") != expected_environment
        or type(value.get("requiredReviewerCount")) is not int
        or value["requiredReviewerCount"] < 1
    ):
        raise ValueError("environment-protection-evidence-invalid")
    return {
        "environment": expected_environment,
        "path": path.name,
        "requiredReviewerCount": value["requiredReviewerCount"],
        "sha256": file_sha256(path),
    }

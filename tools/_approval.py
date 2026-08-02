"""Validate GitHub Environment approval identities supplied by trusted workflows."""

from __future__ import annotations

import re

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
        "actorId": match.group("actor_id"),
        "attempt": match.group("attempt"),
        "environment": match.group("environment"),
        "repositoryId": match.group("repository_id"),
        "runId": match.group("run_id"),
        "type": "github-environment",
    }

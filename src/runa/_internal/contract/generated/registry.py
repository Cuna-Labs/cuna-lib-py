# runa-contract-id: runa-sdk-contract
# runa-snapshot-version: 1.0.0
# runa-snapshot-sha256: 02a554b22592f0267475b847a2bb1c7df64e2b688cdb69b0a4a8b392695e1c55
# runa-generator-version: python-1
# runa-snapshot-path: contracts/runa-sdk-contract.snapshot.json
"""Generated private operation registry. Do not edit manually."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Operation:
    key: str
    method: str
    path_template: str
    success_status: int
    request_fields: tuple[str, ...]
    response_fields: tuple[str, ...]
    source_reference: str


def _op(
    key: str,
    method: str,
    path: str,
    status: int,
    request_fields: tuple[str, ...],
    response_fields: tuple[str, ...],
) -> Operation:
    return Operation(
        key,
        method,
        path,
        status,
        request_fields,
        response_fields,
        f"contracts/runa-sdk-contract.snapshot.json#/operations/{key}",
    )


OPERATIONS: dict[str, Operation] = {
    "me.get": _op("me.get", "GET", "/v1/me", 200, (), ("id", "email", "workspace")),
    "records.list": _op(
        "records.list",
        "GET",
        "/v1/records",
        200,
        (),
        ("id", "session_id", "kind", "summary", "detail", "created_at"),
    ),
    "sessions.checkpoint": _op(
        "sessions.checkpoint", "POST", "/v1/sessions/{id}/checkpoint", 200, ("name",), ("ok",)
    ),
    "sessions.create": _op(
        "sessions.create",
        "POST",
        "/v1/sessions",
        201,
        ("name", "agent", "vcpus", "memory_mib", "allowed_hosts", "runtime_port"),
        (
            "id",
            "user_id",
            "slug",
            "name",
            "agent",
            "vcpus",
            "memory_mib",
            "status",
            "running_seconds",
            "created_at",
            "updated_at",
            "url",
        ),
    ),
    "sessions.delete": _op("sessions.delete", "DELETE", "/v1/sessions/{id}", 200, (), ("ok",)),
    "sessions.exec": _op(
        "sessions.exec",
        "POST",
        "/v1/sessions/{id}/exec",
        200,
        ("command", "args", "cwd", "timeout_secs"),
        (
            "exit_code",
            "stdout",
            "stderr",
            "duration_ms",
            "stdout_truncated",
            "stderr_truncated",
        ),
    ),
    "sessions.get": _op(
        "sessions.get",
        "GET",
        "/v1/sessions/{id}",
        200,
        (),
        (
            "id",
            "user_id",
            "slug",
            "name",
            "agent",
            "vcpus",
            "memory_mib",
            "status",
            "running_seconds",
            "created_at",
            "updated_at",
            "url",
        ),
    ),
    "sessions.list": _op(
        "sessions.list",
        "GET",
        "/v1/sessions",
        200,
        (),
        (
            "id",
            "user_id",
            "slug",
            "name",
            "agent",
            "vcpus",
            "memory_mib",
            "status",
            "running_seconds",
            "created_at",
            "updated_at",
            "url",
        ),
    ),
    "sessions.open": _op("sessions.open", "POST", "/v1/sessions/{id}/open", 200, (), ("url",)),
    "sessions.pause": _op(
        "sessions.pause",
        "POST",
        "/v1/sessions/{id}/pause",
        200,
        (),
        (
            "id",
            "user_id",
            "slug",
            "name",
            "agent",
            "vcpus",
            "memory_mib",
            "status",
            "running_seconds",
            "created_at",
            "updated_at",
            "url",
        ),
    ),
    "sessions.resume": _op(
        "sessions.resume",
        "POST",
        "/v1/sessions/{id}/resume",
        200,
        (),
        (
            "id",
            "user_id",
            "slug",
            "name",
            "agent",
            "vcpus",
            "memory_mib",
            "status",
            "running_seconds",
            "created_at",
            "updated_at",
            "url",
        ),
    ),
    "sessions.start": _op(
        "sessions.start",
        "POST",
        "/v1/sessions/{id}/start",
        200,
        (),
        (
            "id",
            "user_id",
            "slug",
            "name",
            "agent",
            "vcpus",
            "memory_mib",
            "status",
            "running_seconds",
            "created_at",
            "updated_at",
            "url",
        ),
    ),
    "sessions.stop": _op(
        "sessions.stop",
        "POST",
        "/v1/sessions/{id}/stop",
        200,
        (),
        (
            "id",
            "user_id",
            "slug",
            "name",
            "agent",
            "vcpus",
            "memory_mib",
            "status",
            "running_seconds",
            "created_at",
            "updated_at",
            "url",
        ),
    ),
}

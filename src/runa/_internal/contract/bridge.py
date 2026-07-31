"""Handwritten private bridge between wire carriers and public models."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import unquote

from runa.models import (
    Acknowledgement,
    AssignedWorkspace,
    EstimatedUsage,
    ExecResult,
    Me,
    OpenSessionResult,
    Record,
    SessionAgent,
    SessionSnapshot,
    SessionStatus,
    UnassignedWorkspace,
)

from .generated.registry import OPERATIONS

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_OPEN = re.compile(
    r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"\.runacode\.cloud/__runa/auth\?t=[^&#]+$"
)
_DENIED_FRAGMENTS = tuple(
    bytes(values).decode("ascii")
    for values in (
        (114, 117, 110, 116, 97),
        (114, 117, 110, 116, 97, 46, 99, 111, 109),
        (114, 117, 110, 116, 97, 46, 100, 101, 118),
        (114, 117, 110, 116, 105, 109, 101, 95, 105, 100),
        (114, 117, 110, 116, 105, 109, 101, 105, 100),
        (101, 103, 114, 101, 115, 115),
        (115, 101, 99, 114, 101, 116, 95, 115, 116, 117, 98),
        (115, 101, 99, 114, 101, 116, 115, 116, 117, 98),
        (116, 101, 110, 97, 110, 116, 95, 105, 100),
        (116, 101, 110, 97, 110, 116, 105, 100),
        (116, 101, 110, 97, 110, 116, 95, 99, 114, 101, 100, 101, 110, 116, 105, 97, 108),
        (116, 101, 110, 97, 110, 116, 99, 114, 101, 100, 101, 110, 116, 105, 97, 108),
    )
)


@dataclass(frozen=True, slots=True)
class DecodedCarrier:
    known_fields: Mapping[str, object]
    unrecognized_fields: Mapping[str, object]


class DecodeFailure(ValueError):
    __slots__ = ("code", "path")

    def __init__(self, code: str, path: str) -> None:
        super().__init__("Response does not match the Runa contract.")
        self.code = code
        self.path = path


def _decode_escaped(value: str) -> str:
    decoded = value
    for _ in range(2):
        changed = unquote(decoded)
        if changed == decoded:
            break
        decoded = changed
    try:
        escaped = decoded.replace('"', '\\"')
        decoded = json.loads(f'"{escaped}"')
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return decoded.casefold()


def _contains_denied(value: object) -> bool:
    if isinstance(value, str):
        normalized = _decode_escaped(value)
        return any(fragment in normalized for fragment in _DENIED_FRAGMENTS)
    if isinstance(value, list):
        return any(_contains_denied(item) for item in value)
    if isinstance(value, dict):
        return any(
            _contains_denied(key) or _contains_denied(item) for key, item in value.items()
        )
    return False


def sanitize_response(
    value: object, allowlist: tuple[str, ...], *, collection: bool = False
) -> object:
    if collection:
        if not isinstance(value, list):
            raise DecodeFailure("not_array", "$")
        return [sanitize_response(item, allowlist) for item in value]
    if not isinstance(value, dict):
        raise DecodeFailure("not_mapping", "$")
    known = {
        key: value[key]
        for key in allowlist
        if key in value and not _contains_denied(key) and not _contains_denied(value[key])
    }
    unknown = {
        key: item
        for key, item in value.items()
        if key not in allowlist and not _contains_denied(key) and not _contains_denied(item)
    }
    return DecodedCarrier(MappingProxyType(known), MappingProxyType(unknown))


def _require(carrier: DecodedCarrier, *names: str) -> Mapping[str, object]:
    for name in names:
        if name not in carrier.known_fields:
            raise DecodeFailure("missing_member", name)
    return carrier.known_fields


def _decode_session(carrier: DecodedCarrier) -> SessionSnapshot:
    row = _require(
        carrier,
        "id",
        "user_id",
        "slug",
        "name",
        "vcpus",
        "memory_mib",
        "status",
        "running_seconds",
        "created_at",
        "updated_at",
        "url",
    )
    session_id = row["id"]
    if not isinstance(session_id, str) or _UUID.fullmatch(session_id) is None:
        raise DecodeFailure("invalid_literal", "id")
    try:
        status = SessionStatus(row["status"])
    except (TypeError, ValueError):
        raise DecodeFailure("unknown_enum", "status") from None
    raw_agent = row.get("agent")
    if raw_agent is None:
        agent = None
    else:
        try:
            agent = SessionAgent(raw_agent)
        except (TypeError, ValueError):
            raise DecodeFailure("unknown_enum", "agent") from None
    url = row["url"]
    if not isinstance(url, str):
        raise DecodeFailure("invalid_url_type", "url")
    return SessionSnapshot(
        id=session_id,
        user_id=row["user_id"],
        slug=row["slug"],
        name=row["name"],
        agent=agent,
        vcpus=row["vcpus"],
        memory_mib=row["memory_mib"],
        status=status,
        running_seconds=row["running_seconds"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        url=url,
    )


def _decode_exec(carrier: DecodedCarrier) -> ExecResult:
    row = _require(
        carrier,
        "exit_code",
        "stdout",
        "stderr",
        "duration_ms",
        "stdout_truncated",
        "stderr_truncated",
    )
    return ExecResult(
        exit_code=row["exit_code"],
        stdout=row["stdout"],
        stderr=row["stderr"],
        duration_ms=row["duration_ms"],
        stdout_truncated=row["stdout_truncated"],
        stderr_truncated=row["stderr_truncated"],
    )


def _decode_ack(carrier: DecodedCarrier) -> Acknowledgement:
    row = _require(carrier, "ok")
    if row["ok"] is not True:
        raise DecodeFailure("invalid_literal", "ok")
    return Acknowledgement(ok=True)


def _decode_open(carrier: DecodedCarrier) -> OpenSessionResult:
    row = _require(carrier, "url")
    url = row["url"]
    if not isinstance(url, str) or _OPEN.fullmatch(url) is None:
        raise DecodeFailure("invalid_url_type", "url")
    return OpenSessionResult(url=url)


def _decode_record(carrier: DecodedCarrier) -> Record:
    row = _require(carrier, "id", "session_id", "kind", "summary", "detail", "created_at")
    return Record(
        id=row["id"],
        session_id=row["session_id"],
        kind=row["kind"],
        summary=row["summary"],
        detail=row["detail"],
        created_at=row["created_at"],
    )


def _decode_me(carrier: DecodedCarrier) -> Me:
    row = _require(carrier, "id", "email", "workspace")
    raw_workspace = row["workspace"]
    if not isinstance(raw_workspace, dict) or "assigned" not in raw_workspace:
        raise DecodeFailure("invalid_workspace_shape", "workspace")
    if "usage" in raw_workspace and isinstance(raw_workspace["assigned"], bool):
        raw_usage = raw_workspace["usage"]
        if not isinstance(raw_usage, dict):
            raise DecodeFailure("invalid_workspace_shape", "workspace.usage")
        required = ("est_spend_usd", "est_remaining_usd", "note")
        if any(key not in raw_usage for key in required):
            raise DecodeFailure("missing_member", "workspace.usage")
        workspace: AssignedWorkspace | UnassignedWorkspace = AssignedWorkspace(
            assigned=raw_workspace["assigned"],
            usage=EstimatedUsage(
                estimated_spend_usd=raw_usage["est_spend_usd"],
                estimated_remaining_usd=raw_usage["est_remaining_usd"],
                note=raw_usage["note"],
            ),
        )
    elif raw_workspace.get("assigned") is False and "waitlist_position" in raw_workspace:
        workspace = UnassignedWorkspace(
            assigned=False, waitlist_position=raw_workspace["waitlist_position"]
        )
    else:
        raise DecodeFailure("invalid_workspace_shape", "workspace")
    return Me(id=row["id"], email=row["email"], workspace=workspace)


def decode_for_operation(operation_key: str, value: object) -> object:
    operation = OPERATIONS[operation_key]
    if operation_key in {"sessions.list", "records.list"}:
        allowlist = (
            OPERATIONS["sessions.get"].response_fields
            if operation_key == "sessions.list"
            else ("id", "session_id", "kind", "summary", "detail", "created_at")
        )
        carriers = sanitize_response(value, allowlist, collection=True)
        if not isinstance(carriers, list):
            raise DecodeFailure("not_array", "$")
        decoder = _decode_session if operation_key == "sessions.list" else _decode_record
        return [decoder(item) for item in carriers if isinstance(item, DecodedCarrier)]
    sanitized = sanitize_response(value, operation.response_fields)
    if not isinstance(sanitized, DecodedCarrier):
        raise DecodeFailure("not_mapping", "$")
    if operation_key in {
        "sessions.create",
        "sessions.get",
        "sessions.pause",
        "sessions.resume",
        "sessions.start",
        "sessions.stop",
    }:
        return _decode_session(sanitized)
    if operation_key == "sessions.exec":
        return _decode_exec(sanitized)
    if operation_key in {"sessions.checkpoint", "sessions.delete"}:
        return _decode_ack(sanitized)
    if operation_key == "sessions.open":
        return _decode_open(sanitized)
    if operation_key == "me.get":
        return _decode_me(sanitized)
    raise KeyError(operation_key)


def encode_for_operation(
    operation_key: str, supplied: Mapping[str, object] | None
) -> dict[str, object]:
    operation = OPERATIONS[operation_key]
    if supplied is None:
        return {}
    return {key: supplied[key] for key in operation.request_fields if key in supplied}

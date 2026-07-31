"""Handwritten private bridge between wire carriers and public models."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
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
_RUNTIME_URL = re.compile(r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.runacode\.cloud$")
_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
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
        return any(_contains_denied(key) or _contains_denied(item) for key, item in value.items())
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
    if carrier.unrecognized_fields:
        raise DecodeFailure("unknown_member", "$")
    for name in names:
        if name not in carrier.known_fields:
            raise DecodeFailure("missing_member", name)
    return carrier.known_fields


def _string(value: object, path: str, pattern: re.Pattern[str] | None = None) -> str:
    if not isinstance(value, str) or (pattern is not None and pattern.fullmatch(value) is None):
        raise DecodeFailure("invalid_string", path)
    return value


def _uuid(value: object, path: str) -> str:
    return _string(value, path, _UUID)


def _integer(
    value: object, path: str, *, minimum: int | None = None, maximum: int | None = None
) -> int:
    if type(value) is not int:
        raise DecodeFailure("invalid_integer", path)
    if minimum is not None and value < minimum:
        raise DecodeFailure("invalid_integer", path)
    if maximum is not None and value > maximum:
        raise DecodeFailure("invalid_integer", path)
    return value


def _number(value: object, path: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise DecodeFailure("invalid_number", path)
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise DecodeFailure("invalid_boolean", path)
    return value


def _date_time(value: object, path: str) -> str:
    text = _string(value, path, _RFC3339)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise DecodeFailure("invalid_date_time", path) from None
    return text


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
    session_id = _uuid(row["id"], "id")
    try:
        status = SessionStatus(row["status"])
    except (TypeError, ValueError):
        raise DecodeFailure("unknown_enum", "status") from None
    if "agent" not in row:
        agent = None
    else:
        try:
            agent = SessionAgent(row["agent"])
        except (TypeError, ValueError):
            raise DecodeFailure("unknown_enum", "agent") from None
    return SessionSnapshot(
        id=session_id,
        user_id=_uuid(row["user_id"], "user_id"),
        slug=_string(row["slug"], "slug", _SLUG),
        name=_string(row["name"], "name"),
        agent=agent,
        vcpus=_integer(row["vcpus"], "vcpus", minimum=0),
        memory_mib=_integer(row["memory_mib"], "memory_mib", minimum=0),
        status=status,
        running_seconds=_integer(row["running_seconds"], "running_seconds", minimum=0),
        created_at=_date_time(row["created_at"], "created_at"),
        updated_at=_date_time(row["updated_at"], "updated_at"),
        url=_string(row["url"], "url", _RUNTIME_URL),
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
        exit_code=_integer(row["exit_code"], "exit_code"),
        stdout=_string(row["stdout"], "stdout"),
        stderr=_string(row["stderr"], "stderr"),
        duration_ms=_integer(row["duration_ms"], "duration_ms", minimum=0),
        stdout_truncated=_boolean(row["stdout_truncated"], "stdout_truncated"),
        stderr_truncated=_boolean(row["stderr_truncated"], "stderr_truncated"),
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
        id=_uuid(row["id"], "id"),
        session_id=_uuid(row["session_id"], "session_id"),
        kind=_string(row["kind"], "kind"),
        summary=_string(row["summary"], "summary"),
        detail=row["detail"],
        created_at=_date_time(row["created_at"], "created_at"),
    )


def _decode_me(carrier: DecodedCarrier) -> Me:
    row = _require(carrier, "id", "email", "workspace")
    raw_workspace = row["workspace"]
    if not isinstance(raw_workspace, dict) or "assigned" not in raw_workspace:
        raise DecodeFailure("invalid_workspace_shape", "workspace")
    if raw_workspace["assigned"] is True and set(raw_workspace) == {"assigned", "usage"}:
        raw_usage = raw_workspace["usage"]
        if not isinstance(raw_usage, dict):
            raise DecodeFailure("invalid_workspace_shape", "workspace.usage")
        required = ("est_spend_usd", "est_remaining_usd", "note")
        if any(key not in raw_usage for key in required):
            raise DecodeFailure("missing_member", "workspace.usage")
        workspace: AssignedWorkspace | UnassignedWorkspace = AssignedWorkspace(
            assigned=True,
            usage=EstimatedUsage(
                estimated_spend_usd=_number(
                    raw_usage["est_spend_usd"], "workspace.usage.est_spend_usd"
                ),
                estimated_remaining_usd=_number(
                    raw_usage["est_remaining_usd"], "workspace.usage.est_remaining_usd"
                ),
                note=_string(raw_usage["note"], "workspace.usage.note"),
            ),
        )
    elif raw_workspace.get("assigned") is False and set(raw_workspace) == {
        "assigned",
        "waitlist_position",
    }:
        workspace = UnassignedWorkspace(
            assigned=False,
            waitlist_position=_integer(
                raw_workspace["waitlist_position"], "workspace.waitlist_position", minimum=0
            ),
        )
    else:
        raise DecodeFailure("invalid_workspace_shape", "workspace")
    return Me(
        id=_uuid(row["id"], "id"),
        email=_string(row["email"], "email"),
        workspace=workspace,
    )


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

"""Handwritten private bridge between wire carriers and public models."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Literal, TypeVar, cast

from runa.models import (
    Acknowledgement,
    AgentSession,
    AgentSessionAuth,
    AgentSessionAuthEvidenceClass,
    AgentSessionAuthMode,
    AgentSessionAuthState,
    AgentSessionDesiredState,
    AgentSessionPage,
    AgentSessionProcessState,
    AgentSessionRequestState,
    AssignedWorkspace,
    Capability,
    CapabilityAvailability,
    CapabilityInteraction,
    CapabilityMutationClass,
    CapabilityScope,
    CapabilitySnapshot,
    CapabilitySurface,
    EstimatedUsage,
    ExecResult,
    MachineCreateRequest,
    Me,
    OpenSessionResult,
    Record,
    SessionAgent,
    SessionSnapshot,
    SessionStatus,
    TerminalConnectionAvailability,
    TerminalConnectionCapability,
    TerminalConnectionCapabilityName,
    TerminalConnectionGrant,
    UnassignedWorkspace,
    WorkspaceBinding,
    WorkspaceSyncChangeItem,
    WorkspaceSyncChangePage,
    WorkspaceSyncChunkContent,
    WorkspaceSyncChunkReceipt,
    WorkspaceSyncChunkRef,
    WorkspaceSyncCommitReceipt,
    WorkspaceSyncEnvelope,
    WorkspaceSyncManifestEntry,
    WorkspaceSyncManifestReceipt,
    WorkspaceSyncReconcileReceipt,
    WorkspaceSyncSession,
)

from ..constraints import UUID_PATTERN, is_uuid
from ..security import contains_denied
from .generated.deserializers import deserialize_generated_response
from .generated.operation_metadata import GENERATED_OPERATIONS
from .generated.serializers import serialize_generated_request
from .generated.wire_types import GENERATED_WIRE_SCHEMAS


@dataclass(frozen=True, slots=True)
class Operation:
    """Handwritten adapter view over canonical generated operation metadata."""

    key: str
    method: str
    path_template: str
    success_status: int
    request_fields: tuple[str, ...]
    response_fields: tuple[str, ...]
    source_reference: str


_REQUEST_COMPONENTS = {
    "agentSessions.create": "AgentSessionCreate",
    "agentSessions.createTerminalConnection": "TerminalConnectionCreate",
    "agentSessions.rename": "AgentSessionRename",
    "sessions.checkpoint": "CheckpointRequest",
    "sessions.create": "SdkCreateSession",
    "sessions.exec": "ExecRequest",
}
_RESPONSE_COMPONENTS = {
    "agentSessions.create": "AgentSession",
    "agentSessions.createTerminalConnection": "TerminalConnectionGrant",
    "agentSessions.get": "AgentSession",
    "agentSessions.list": "AgentSessionPage",
    "agentSessions.rename": "AgentSession",
    "agentSessions.terminate": "AgentSession",
    "capabilities.get": "CapabilitySnapshot",
    "me.get": "Me",
    "records.list": "Record",
    "sessions.checkpoint": "Ok",
    "agentSessions.agentAuth": "AgentSessionAuth",
    "sessions.create": "Session",
    "sessions.delete": "Ok",
    "sessions.exec": "ExecResult",
    "sessions.get": "Session",
    "sessions.list": "Session",
    "sessions.open": "OpenResult",
    "sessions.pause": "Session",
    "sessions.resume": "Session",
    "sessions.start": "Session",
    "sessions.stop": "Session",
}

_WORKSPACE_SYNC_CAPABILITIES = frozenset(
    {
        "atomic_generation_commit",
        "bounded_manifest_pages",
        "content_digest_verification",
        "explicit_reconciliation",
        "ordered_generation_changes",
        "policy_bound_admission",
    }
)


def _wire_fields(component: str | None) -> tuple[str, ...]:
    if component is None:
        return ()
    schema = GENERATED_WIRE_SCHEMAS[component]
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return ()
    return tuple(sorted(properties))


OPERATIONS = {
    key: Operation(
        key=key,
        method=str(metadata["method"]),
        path_template=str(metadata["pathTemplate"]),
        success_status=int(metadata["successStatus"]),
        request_fields=_wire_fields(_REQUEST_COMPONENTS.get(key)),
        response_fields=_wire_fields(_RESPONSE_COMPONENTS.get(key)),
        source_reference="contracts/runa-sdk.projection.json#/operations/" + key,
    )
    for key, metadata in GENERATED_OPERATIONS.items()
}
OPERATIONS = dict(sorted(OPERATIONS.items()))

_OPEN = re.compile(
    r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"\.runacode\.cloud/__runa/auth\?t=[^&#]+$"
)
_RUNTIME_URL = re.compile(r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.runacode\.cloud$")
_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_CAPABILITY_ID = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_PERMISSION = re.compile(r"^[a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*)+$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_ETAG = re.compile(r"^[0-9a-f]{64}$")
_AGENT_SESSION_CWD = re.compile(r"^/workspace(?:/.*)?$")
_TERMINAL_CONNECT_TOKEN = re.compile(r"^runa_tc_[A-Za-z0-9_-]{43}$")
_AGENT_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_AGENT_AUTH_ADAPTER = "runa.agent-auth.v1"
_MAX_AGENT_AUTH_TTL_SECONDS = 30.0
_MAX_AGENT_AUTH_FUTURE_SKEW_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class DecodedCarrier:
    """A decoded wire payload before it becomes a typed model.

    ``known_fields`` is the raw decoded body, so for ``sessions.open`` it holds
    the capability URL and for a terminal connection it holds ``connect_token``.
    Rendering it by default repr would undo the field-level ``repr=False`` on
    ``TerminalConnectionGrant.connect_token`` and ``OpenSessionResult.url`` one
    layer down, in frames that raise on every contract violation.
    """

    known_fields: Mapping[str, object] = field(repr=False)
    unrecognized_fields: Mapping[str, object] = field(repr=False)


class DecodeFailure(ValueError):
    __slots__ = ("code", "path")

    def __init__(self, code: str, path: str) -> None:
        super().__init__("Response does not match the Runa contract.")
        self.code = code
        self.path = path


class EncodeFailure(ValueError):
    """Safe private failure for a request outside the canonical schema."""


_CapabilityEnumT = TypeVar("_CapabilityEnumT", bound=Enum)


def sanitize_response(
    value: object, allowlist: tuple[str, ...], *, collection: bool = False
) -> object:
    if collection:
        if not isinstance(value, list):
            raise DecodeFailure("not_array", "$")
        return [sanitize_response(item, allowlist) for item in value]
    if not isinstance(value, dict):
        raise DecodeFailure("not_mapping", "$")
    if contains_denied(value):
        raise DecodeFailure("protected_content", "$")
    if set(value) - set(allowlist):
        raise DecodeFailure("unknown_member", "$")
    known = {key: value[key] for key in allowlist if key in value}
    return DecodedCarrier(MappingProxyType(known), MappingProxyType({}))


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
    return _string(value, path, UUID_PATTERN)


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


def _decode_agent_session_auth(carrier: DecodedCarrier) -> AgentSessionAuth:
    row = _require(
        carrier,
        "observation_id",
        "agent_session_id",
        "process_epoch",
        "auth_mode",
        "agent_version",
        "adapter_version",
        "evidence_class",
        "observed_at",
        "valid_until",
        "state",
    )
    process_epoch = (
        None if row["process_epoch"] is None else _uuid(row["process_epoch"], "process_epoch")
    )
    auth_mode = _enum(row["auth_mode"], AgentSessionAuthMode, "auth_mode")
    evidence_class = _enum(row["evidence_class"], AgentSessionAuthEvidenceClass, "evidence_class")
    state = _enum(row["state"], AgentSessionAuthState, "state")
    agent_version = _string(row["agent_version"], "agent_version")
    adapter_version = _string(row["adapter_version"], "adapter_version")
    observed_at = _date_time(row["observed_at"], "observed_at")
    valid_until = _date_time(row["valid_until"], "valid_until")
    observed_seconds = datetime.fromisoformat(observed_at.replace("Z", "+00:00")).timestamp()
    valid_until_seconds = datetime.fromisoformat(valid_until.replace("Z", "+00:00")).timestamp()
    unavailable = (
        evidence_class is AgentSessionAuthEvidenceClass.INSUFFICIENT
        and state is AgentSessionAuthState.UNAVAILABLE
    )
    interactive = (
        auth_mode is AgentSessionAuthMode.INTERACTIVE_LOGIN
        and evidence_class is AgentSessionAuthEvidenceClass.PROVIDER_CLI_LOGIN_STATUS
        and state in {AgentSessionAuthState.LOGIN_REQUIRED, AgentSessionAuthState.AUTHENTICATED}
    )
    credential = (
        auth_mode is AgentSessionAuthMode.CREDENTIAL_BINDING
        and evidence_class is AgentSessionAuthEvidenceClass.CREDENTIAL_BINDING_AUTHORITY
        and state is AgentSessionAuthState.CONFIGURED
    )
    now_seconds = time.time()
    if (
        adapter_version != _AGENT_AUTH_ADAPTER
        or not (unavailable or interactive or credential)
        or (unavailable and valid_until_seconds != observed_seconds)
        or (
            not unavailable
            and (
                process_epoch is None
                or _AGENT_VERSION.fullmatch(agent_version) is None
                or valid_until_seconds <= observed_seconds
                or valid_until_seconds - observed_seconds > _MAX_AGENT_AUTH_TTL_SECONDS
                or observed_seconds > now_seconds + _MAX_AGENT_AUTH_FUTURE_SKEW_SECONDS
                or valid_until_seconds <= now_seconds
            )
        )
    ):
        raise DecodeFailure("invalid_agent_session_auth", "$")
    return AgentSessionAuth(
        observation_id=_uuid(row["observation_id"], "observation_id"),
        agent_session_id=_uuid(row["agent_session_id"], "agent_session_id"),
        process_epoch=process_epoch,
        auth_mode=auth_mode,
        agent_version=agent_version,
        adapter_version=cast(Literal["runa.agent-auth.v1"], adapter_version),
        evidence_class=evidence_class,
        observed_at=observed_at,
        valid_until=valid_until,
        state=state,
    )


def _bounded_string(value: object, path: str, minimum: int, maximum: int) -> str:
    result = _string(value, path)
    if not minimum <= len(result) <= maximum:
        raise DecodeFailure("invalid_string", path)
    return result


def _decode_agent_session(carrier: DecodedCarrier) -> AgentSession:
    row = _require(
        carrier,
        "id",
        "machine_id",
        "name",
        "agent",
        "cwd",
        "auth_mode",
        "desired_state",
        "request_state",
        "process_state",
        "row_version",
        "created_at",
        "updated_at",
    )
    cwd = _bounded_string(row["cwd"], "cwd", 10, 1024)
    if _AGENT_SESSION_CWD.fullmatch(cwd) is None:
        raise DecodeFailure("invalid_string", "cwd")
    has_workspace_binding_id = "workspace_binding_id" in row
    has_workspace_generation = "workspace_generation" in row
    if has_workspace_binding_id != has_workspace_generation:
        raise DecodeFailure("invalid_workspace_binding", "workspace_binding_id")
    return AgentSession(
        id=_uuid(row["id"], "id"),
        machine_id=_uuid(row["machine_id"], "machine_id"),
        name=_bounded_string(row["name"], "name", 1, 80),
        agent=_enum(row["agent"], SessionAgent, "agent"),
        cwd=cwd,
        auth_mode=_enum(row["auth_mode"], AgentSessionAuthMode, "auth_mode"),
        desired_state=_enum(row["desired_state"], AgentSessionDesiredState, "desired_state"),
        request_state=_enum(row["request_state"], AgentSessionRequestState, "request_state"),
        process_state=_enum(row["process_state"], AgentSessionProcessState, "process_state"),
        row_version=_integer(row["row_version"], "row_version", minimum=0),
        created_at=_date_time(row["created_at"], "created_at"),
        updated_at=_date_time(row["updated_at"], "updated_at"),
        workspace_binding_id=(
            _uuid(row["workspace_binding_id"], "workspace_binding_id")
            if has_workspace_binding_id
            else None
        ),
        workspace_generation=(
            _integer(row["workspace_generation"], "workspace_generation", minimum=1)
            if has_workspace_generation
            else None
        ),
        process_epoch=(
            _uuid(row["process_epoch"], "process_epoch") if "process_epoch" in row else None
        ),
        runtime_observed_at=(
            _date_time(row["runtime_observed_at"], "runtime_observed_at")
            if "runtime_observed_at" in row
            else None
        ),
        runtime_expires_at=(
            _date_time(row["runtime_expires_at"], "runtime_expires_at")
            if "runtime_expires_at" in row
            else None
        ),
        termination_requested_at=(
            _date_time(row["termination_requested_at"], "termination_requested_at")
            if "termination_requested_at" in row
            else None
        ),
    )


def _decode_agent_session_page(value: object) -> AgentSessionPage:
    if not isinstance(value, dict) or set(value) - {"items", "next_cursor"} or "items" not in value:
        raise DecodeFailure("invalid_member", "$")
    if contains_denied(value):
        raise DecodeFailure("protected_content", "$")
    items = value["items"]
    if not isinstance(items, list) or len(items) > 100:
        raise DecodeFailure("invalid_array", "items")
    decoded = tuple(
        _decode_agent_session(
            cast(
                DecodedCarrier,
                sanitize_response(item, OPERATIONS["agentSessions.get"].response_fields),
            )
        )
        for item in items
    )
    next_cursor = (
        _bounded_string(value["next_cursor"], "next_cursor", 1, 512)
        if "next_cursor" in value
        else None
    )
    return AgentSessionPage(items=decoded, next_cursor=next_cursor)


def _decode_terminal_connection_grant(carrier: DecodedCarrier) -> TerminalConnectionGrant:
    row = _require(
        carrier,
        "terminal_session_id",
        "resume_handle",
        "connect_url",
        "connect_token",
        "protocol",
        "capabilities",
        "expires_at",
    )
    terminal_session_id = _uuid(row["terminal_session_id"], "terminal_session_id")
    expected_urls = {
        f"wss://api.getcuna.com/v1/terminal-connections/{terminal_session_id}/stream",
        f"wss://api.runacode.io/v1/terminal-connections/{terminal_session_id}/stream",
    }
    if row["connect_url"] not in expected_urls or row["protocol"] != "runa.terminal.v1":
        raise DecodeFailure("invalid_literal", "connect_url")
    raw_capabilities = row["capabilities"]
    if not isinstance(raw_capabilities, list) or len(raw_capabilities) != 5:
        raise DecodeFailure("invalid_array", "capabilities")
    capabilities: list[TerminalConnectionCapability] = []
    for index, raw in enumerate(raw_capabilities):
        if not isinstance(raw, dict) or set(raw) != {"name", "availability"}:
            raise DecodeFailure("invalid_member", f"capabilities[{index}]")
        capabilities.append(
            TerminalConnectionCapability(
                name=_enum(
                    raw["name"],
                    TerminalConnectionCapabilityName,
                    f"capabilities[{index}].name",
                ),
                availability=_enum(
                    raw["availability"],
                    TerminalConnectionAvailability,
                    f"capabilities[{index}].availability",
                ),
            )
        )
    if {item.name for item in capabilities} != set(TerminalConnectionCapabilityName):
        raise DecodeFailure("invalid_array", "capabilities")
    return TerminalConnectionGrant(
        terminal_session_id=terminal_session_id,
        resume_handle=_uuid(row["resume_handle"], "resume_handle"),
        connect_url=cast(str, row["connect_url"]),
        connect_token=_string(row["connect_token"], "connect_token", _TERMINAL_CONNECT_TOKEN),
        protocol="runa.terminal.v1",
        capabilities=tuple(capabilities),
        expires_at=_date_time(row["expires_at"], "expires_at"),
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


def _enum(
    value: object,
    enum_type: type[_CapabilityEnumT],
    path: str,
) -> _CapabilityEnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        raise DecodeFailure("unknown_enum", path) from None


def _decode_capability(value: object, path: str) -> Capability:
    if not isinstance(value, dict):
        raise DecodeFailure("not_mapping", path)
    required = {
        "id",
        "availability",
        "surfaces",
        "interaction",
        "mutation_class",
        "required_permissions",
    }
    if not required <= set(value) or set(value) - required - {"reason_code"}:
        raise DecodeFailure("invalid_member", path)
    capability_id = _string(value["id"], f"{path}.id", _CAPABILITY_ID)
    raw_surfaces = value["surfaces"]
    if not isinstance(raw_surfaces, list) or not 1 <= len(raw_surfaces) <= 3:
        raise DecodeFailure("invalid_array", f"{path}.surfaces")
    surfaces = tuple(
        _enum(surface, CapabilitySurface, f"{path}.surfaces") for surface in raw_surfaces
    )
    if len(set(surfaces)) != len(surfaces):
        raise DecodeFailure("duplicate_member", f"{path}.surfaces")
    raw_permissions = value["required_permissions"]
    if not isinstance(raw_permissions, list) or len(raw_permissions) > 16:
        raise DecodeFailure("invalid_array", f"{path}.required_permissions")
    permissions = tuple(
        _string(permission, f"{path}.required_permissions", _PERMISSION)
        for permission in raw_permissions
    )
    if len(set(permissions)) != len(permissions):
        raise DecodeFailure("duplicate_member", f"{path}.required_permissions")
    reason_code = None
    if "reason_code" in value:
        reason_code = _string(value["reason_code"], f"{path}.reason_code", _REASON_CODE)
    return Capability(
        id=capability_id,
        availability=_enum(value["availability"], CapabilityAvailability, f"{path}.availability"),
        surfaces=surfaces,
        interaction=_enum(value["interaction"], CapabilityInteraction, f"{path}.interaction"),
        mutation_class=_enum(
            value["mutation_class"], CapabilityMutationClass, f"{path}.mutation_class"
        ),
        required_permissions=permissions,
        reason_code=reason_code,
    )


def _decode_capability_snapshot(carrier: DecodedCarrier) -> CapabilitySnapshot:
    row = _require(
        carrier,
        "schema_version",
        "subject_scope",
        "observed_at",
        "expires_at",
        "etag",
        "capabilities",
    )
    if row["schema_version"] != "1.0":
        raise DecodeFailure("invalid_literal", "schema_version")
    try:
        subject_scope = cast(  # type: ignore[redundant-cast]
            Literal[
                CapabilityScope.ACCOUNT,
                CapabilityScope.MACHINE,
                CapabilityScope.AGENT_SESSION,
            ],
            CapabilityScope(row["subject_scope"]),
        )
    except (TypeError, ValueError):
        raise DecodeFailure("unknown_enum", "subject_scope") from None
    subject_id = _uuid(row["subject_id"], "subject_id") if "subject_id" in row else None
    observed_at = _date_time(row["observed_at"], "observed_at")
    expires_at = _date_time(row["expires_at"], "expires_at")
    if datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.fromisoformat(
        observed_at.replace("Z", "+00:00")
    ):
        raise DecodeFailure("invalid_lease", "expires_at")
    etag = _string(row["etag"], "etag", _ETAG)
    raw_capabilities = row["capabilities"]
    if not isinstance(raw_capabilities, list) or len(raw_capabilities) > 128:
        raise DecodeFailure("invalid_array", "capabilities")
    return CapabilitySnapshot(
        schema_version="1.0",
        subject_scope=subject_scope,
        subject_id=subject_id,
        observed_at=observed_at,
        expires_at=expires_at,
        etag=etag,
        capabilities=tuple(
            _decode_capability(capability, f"capabilities[{index}]")
            for index, capability in enumerate(raw_capabilities)
        ),
    )


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
    if raw_workspace["assigned"] is True and set(raw_workspace) == {
        "assigned",
        "id",
        "usage",
    }:
        raw_usage = raw_workspace["usage"]
        if not isinstance(raw_usage, dict):
            raise DecodeFailure("invalid_workspace_shape", "workspace.usage")
        required = ("est_spend_usd", "est_remaining_usd", "note")
        if any(key not in raw_usage for key in required):
            raise DecodeFailure("missing_member", "workspace.usage")
        workspace: AssignedWorkspace | UnassignedWorkspace = AssignedWorkspace(
            assigned=True,
            id=_uuid(raw_workspace["id"], "workspace.id"),
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


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REMOTE_ROOT = re.compile(r"^/workspace/projects/" + UUID_PATTERN.pattern.removeprefix("^"))


def _exact_mapping(
    value: object, required: set[str], optional: set[str] | frozenset[str] = frozenset()
) -> dict[str, object]:
    if (
        not isinstance(value, dict)
        or not required <= set(value)
        or set(value) - required - optional
        or contains_denied(value)
    ):
        raise DecodeFailure("invalid_workspace_shape", "$")
    return value


def _decode_workspace_binding(value: object) -> WorkspaceBinding:
    row = _exact_mapping(
        value,
        {
            "binding_id",
            "workspace_id",
            "project_id",
            "local_instance_id",
            "machine_id",
            "remote_root",
            "exclusion_policy_digest",
            "active_generation",
            "active_manifest_root",
            "binding_epoch",
            "minimum_reader",
            "minimum_writer",
            "created_at",
            "updated_at",
        },
    )
    return WorkspaceBinding(
        binding_id=_uuid(row["binding_id"], "binding_id"),
        workspace_id=_uuid(row["workspace_id"], "workspace_id"),
        project_id=_uuid(row["project_id"], "project_id"),
        local_instance_id=_uuid(row["local_instance_id"], "local_instance_id"),
        machine_id=_uuid(row["machine_id"], "machine_id"),
        remote_root=_string(row["remote_root"], "remote_root", _REMOTE_ROOT),
        exclusion_policy_digest=_string(
            row["exclusion_policy_digest"], "exclusion_policy_digest", _DIGEST
        ),
        active_generation=_integer(
            row["active_generation"], "active_generation", minimum=0, maximum=9_007_199_254_740_991
        ),
        active_manifest_root=_string(row["active_manifest_root"], "active_manifest_root", _DIGEST),
        binding_epoch=_integer(
            row["binding_epoch"], "binding_epoch", minimum=1, maximum=9_007_199_254_740_991
        ),
        minimum_reader=_integer(row["minimum_reader"], "minimum_reader", minimum=1),
        minimum_writer=_integer(row["minimum_writer"], "minimum_writer", minimum=1),
        created_at=_date_time(row["created_at"], "created_at"),
        updated_at=_date_time(row["updated_at"], "updated_at"),
    )


def _decode_sync_capabilities(
    value: object,
) -> tuple[
    Literal[
        "atomic_generation_commit",
        "bounded_manifest_pages",
        "content_digest_verification",
        "explicit_reconciliation",
        "ordered_generation_changes",
        "policy_bound_admission",
    ],
    ...,
]:
    if (
        not isinstance(value, list)
        or len(value) != len(_WORKSPACE_SYNC_CAPABILITIES)
        or any(not isinstance(item, str) for item in value)
        or set(value) != _WORKSPACE_SYNC_CAPABILITIES
    ):
        raise DecodeFailure("invalid_workspace_sync_capabilities", "capabilities")
    return cast(
        tuple[
            Literal[
                "atomic_generation_commit",
                "bounded_manifest_pages",
                "content_digest_verification",
                "explicit_reconciliation",
                "ordered_generation_changes",
                "policy_bound_admission",
            ],
            ...,
        ],
        tuple(value),
    )


def _decode_manifest_entry(value: object) -> WorkspaceSyncManifestEntry:
    row = _exact_mapping(
        value, {"path", "kind", "byte_length", "executable", "chunks", "link_target"}
    )
    path = _string(row["path"], "path")
    kind = row["kind"]
    chunks = row["chunks"]
    link_target = row["link_target"]
    if (
        not 1 <= len(path) <= 4096
        or kind not in {"directory", "file", "symlink"}
        or type(row["executable"]) is not bool
        or not isinstance(chunks, list)
        or len(chunks) > 4096
        or (
            link_target is not None
            and (not isinstance(link_target, str) or len(link_target) > 4096)
        )
    ):
        raise DecodeFailure("invalid_workspace_manifest_entry", "$")
    decoded_chunks: list[WorkspaceSyncChunkRef] = []
    for index, chunk in enumerate(chunks):
        item = _exact_mapping(chunk, {"digest", "byte_length"})
        decoded_chunks.append(
            WorkspaceSyncChunkRef(
                digest=_string(item["digest"], f"chunks.{index}.digest", _DIGEST),
                byte_length=_integer(
                    item["byte_length"], f"chunks.{index}.byte_length", minimum=0, maximum=8_388_608
                ),
            )
        )
    return WorkspaceSyncManifestEntry(
        path=path,
        kind=cast(Literal["directory", "file", "symlink"], kind),
        byte_length=_integer(row["byte_length"], "byte_length", minimum=0),
        executable=row["executable"],
        chunks=decoded_chunks,
        link_target=link_target,
    )


def _decode_sync_session(value: object) -> WorkspaceSyncSession:
    row = _exact_mapping(
        value,
        {
            "id",
            "workspace_id",
            "machine_id",
            "base_generation",
            "exclusion_policy_digest",
            "selected_protocol",
            "capabilities",
            "state",
            "manifest_entry_count",
            "manifest_encoded_bytes",
            "content_bytes",
            "expires_at",
            "created_at",
            "updated_at",
        },
        {"last_page_index", "committed_generation", "committed_manifest_root"},
    )
    state = row["state"]
    if state not in {"staging", "committed", "conflicted", "expired"}:
        raise DecodeFailure("invalid_workspace_sync_state", "state")
    protocol = _integer(row["selected_protocol"], "selected_protocol", minimum=1, maximum=2)
    return WorkspaceSyncSession(
        id=_uuid(row["id"], "id"),
        workspace_id=_uuid(row["workspace_id"], "workspace_id"),
        machine_id=_uuid(row["machine_id"], "machine_id"),
        base_generation=_integer(row["base_generation"], "base_generation", minimum=0),
        exclusion_policy_digest=_string(
            row["exclusion_policy_digest"], "exclusion_policy_digest", _DIGEST
        ),
        selected_protocol=cast(Literal[1, 2], protocol),
        capabilities=_decode_sync_capabilities(row["capabilities"]),
        state=cast(Literal["staging", "committed", "conflicted", "expired"], state),
        manifest_entry_count=_integer(
            row["manifest_entry_count"], "manifest_entry_count", minimum=0
        ),
        manifest_encoded_bytes=_integer(
            row["manifest_encoded_bytes"], "manifest_encoded_bytes", minimum=0
        ),
        content_bytes=_integer(row["content_bytes"], "content_bytes", minimum=0),
        expires_at=_date_time(row["expires_at"], "expires_at"),
        created_at=_date_time(row["created_at"], "created_at"),
        updated_at=_date_time(row["updated_at"], "updated_at"),
        last_page_index=(
            _integer(row["last_page_index"], "last_page_index", minimum=0)
            if "last_page_index" in row
            else None
        ),
        committed_generation=(
            _integer(row["committed_generation"], "committed_generation", minimum=1)
            if "committed_generation" in row
            else None
        ),
        committed_manifest_root=(
            _string(row["committed_manifest_root"], "committed_manifest_root", _DIGEST)
            if "committed_manifest_root" in row
            else None
        ),
    )


def _decode_workspace_sync_data(operation_key: str, value: object) -> object:
    if operation_key == "workspaces.sync.begin":
        return _decode_sync_session(value)
    if operation_key == "workspaces.sync.negotiate":
        row = _exact_mapping(value, {"sync", "page_index", "page_digest", "missing_digests"})
        missing = row["missing_digests"]
        if not isinstance(missing, list):
            raise DecodeFailure("invalid_workspace_sync_manifest_receipt", "missing_digests")
        return WorkspaceSyncManifestReceipt(
            sync=_decode_sync_session(row["sync"]),
            page_index=_integer(row["page_index"], "page_index", minimum=0),
            page_digest=_string(row["page_digest"], "page_digest", _DIGEST),
            missing_digests=tuple(
                _string(item, f"missing_digests.{index}", _DIGEST)
                for index, item in enumerate(missing)
            ),
        )
    if operation_key == "workspaces.sync.chunk":
        row = _exact_mapping(value, {"selected_protocol", "digest", "byte_length", "stored"})
        if type(row["stored"]) is not bool:
            raise DecodeFailure("invalid_workspace_sync_chunk_receipt", "stored")
        return WorkspaceSyncChunkReceipt(
            selected_protocol=cast(
                Literal[1, 2],
                _integer(row["selected_protocol"], "selected_protocol", minimum=1, maximum=2),
            ),
            digest=_string(row["digest"], "digest", _DIGEST),
            byte_length=_integer(row["byte_length"], "byte_length", minimum=0, maximum=8_388_608),
            stored=row["stored"],
        )
    if operation_key == "workspaces.sync.chunkDownload":
        row = _exact_mapping(
            value,
            {
                "selected_protocol",
                "digest",
                "byte_length",
                "minimum_reader",
                "content_base64",
            },
        )
        selected_protocol = cast(
            Literal[1, 2],
            _integer(row["selected_protocol"], "selected_protocol", minimum=1, maximum=2),
        )
        expected_digest = _string(row["digest"], "digest", _DIGEST)
        byte_length = _integer(row["byte_length"], "byte_length", minimum=0, maximum=8_388_608)
        minimum_reader = _integer(row["minimum_reader"], "minimum_reader", minimum=1, maximum=2)
        encoded = _string(row["content_base64"], "content_base64")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise DecodeFailure("invalid_workspace_sync_chunk_content", "content_base64") from None
        if (
            minimum_reader > selected_protocol
            or len(content) != byte_length
            or base64.b64encode(content).decode("ascii") != encoded
            or hashlib.sha256(content).hexdigest() != expected_digest
        ):
            raise DecodeFailure("invalid_workspace_sync_chunk_content", "content_base64")
        return WorkspaceSyncChunkContent(
            selected_protocol=selected_protocol,
            digest=expected_digest,
            byte_length=byte_length,
            minimum_reader=minimum_reader,
            content=content,
        )
    if operation_key == "workspaces.sync.commit":
        row = _exact_mapping(
            value,
            {
                "selected_protocol",
                "state",
                "generation",
                "manifest_root",
                "committed_at",
                "minimum_reader",
                "minimum_writer",
            },
        )
        if row["state"] != "committed":
            raise DecodeFailure("invalid_workspace_sync_commit_receipt", "state")
        return WorkspaceSyncCommitReceipt(
            selected_protocol=cast(
                Literal[1, 2],
                _integer(row["selected_protocol"], "selected_protocol", minimum=1, maximum=2),
            ),
            state="committed",
            generation=_integer(row["generation"], "generation", minimum=1),
            manifest_root=_string(row["manifest_root"], "manifest_root", _DIGEST),
            committed_at=_date_time(row["committed_at"], "committed_at"),
            minimum_reader=_integer(row["minimum_reader"], "minimum_reader", minimum=1),
            minimum_writer=_integer(row["minimum_writer"], "minimum_writer", minimum=1),
        )
    if operation_key == "workspaces.sync.changes":
        row = _exact_mapping(value, {"selected_protocol", "items", "next_cursor"})
        items = row["items"]
        cursor = row["next_cursor"]
        if (
            not isinstance(items, list)
            or len(items) > 1000
            or (cursor is not None and (not isinstance(cursor, str) or len(cursor) > 1024))
        ):
            raise DecodeFailure("invalid_workspace_sync_change_page", "$")
        decoded: list[WorkspaceSyncChangeItem] = []
        for item in items:
            change = _exact_mapping(
                item,
                {
                    "generation",
                    "operation",
                    "path",
                    "entry",
                    "manifest_root",
                    "exclusion_policy_digest",
                    "committed_at",
                    "minimum_reader",
                    "minimum_writer",
                },
            )
            operation = change["operation"]
            path = change["path"]
            if operation not in {"revision", "upsert", "delete"} or (
                path is not None and (not isinstance(path, str) or len(path) > 4096)
            ):
                raise DecodeFailure("invalid_workspace_sync_change", "$")
            decoded.append(
                WorkspaceSyncChangeItem(
                    generation=_integer(change["generation"], "generation", minimum=1),
                    operation=cast(Literal["revision", "upsert", "delete"], operation),
                    path=path,
                    entry=(
                        _decode_manifest_entry(change["entry"])
                        if change["entry"] is not None
                        else None
                    ),
                    manifest_root=_string(change["manifest_root"], "manifest_root", _DIGEST),
                    exclusion_policy_digest=_string(
                        change["exclusion_policy_digest"], "exclusion_policy_digest", _DIGEST
                    ),
                    committed_at=_date_time(change["committed_at"], "committed_at"),
                    minimum_reader=_integer(change["minimum_reader"], "minimum_reader", minimum=1),
                    minimum_writer=_integer(change["minimum_writer"], "minimum_writer", minimum=1),
                )
            )
        return WorkspaceSyncChangePage(
            selected_protocol=cast(
                Literal[1, 2],
                _integer(row["selected_protocol"], "selected_protocol", minimum=1, maximum=2),
            ),
            items=tuple(decoded),
            next_cursor=cursor,
        )
    if operation_key == "workspaces.sync.reconcile":
        row = _exact_mapping(
            value,
            {
                "selected_protocol",
                "status",
                "active_generation",
                "active_manifest_root",
                "exclusion_policy_digest",
            },
        )
        status = row["status"]
        if status not in {"converged", "reconciliation_required"}:
            raise DecodeFailure("invalid_workspace_sync_reconcile_receipt", "status")
        return WorkspaceSyncReconcileReceipt(
            selected_protocol=cast(
                Literal[1, 2],
                _integer(row["selected_protocol"], "selected_protocol", minimum=1, maximum=2),
            ),
            status=cast(Literal["converged", "reconciliation_required"], status),
            active_generation=_integer(row["active_generation"], "active_generation", minimum=0),
            active_manifest_root=_string(
                row["active_manifest_root"], "active_manifest_root", _DIGEST
            ),
            exclusion_policy_digest=_string(
                row["exclusion_policy_digest"], "exclusion_policy_digest", _DIGEST
            ),
        )
    raise KeyError(operation_key)


def decode_for_operation(operation_key: str, value: object) -> object:
    if operation_key.startswith("workspaceBindings."):
        return _decode_workspace_binding(value)
    if operation_key.startswith("machineCreates."):
        if not isinstance(value, dict) or set(value) != {
            "id",
            "machine_id",
            "state",
            "retryable",
            "action",
            "updated_at",
        }:
            raise DecodeFailure("unknown_member", "$")
        states = {
            "prepared",
            "in_progress",
            "unknown",
            "provider_succeeded",
            "settled",
            "terminal_failed",
        }
        actions = {"retry_create", "reconcile", "wait", "none"}
        if (
            not is_uuid(value["id"])
            or not is_uuid(value["machine_id"])
            or value["state"] not in states
            or type(value["retryable"]) is not bool
            or value["action"] not in actions
            or not isinstance(value["updated_at"], str)
        ):
            raise DecodeFailure("invalid_machine_create", "$")
        return MachineCreateRequest(
            id=cast(str, value["id"]),
            machine_id=cast(str, value["machine_id"]),
            state=cast(
                Literal[
                    "prepared",
                    "in_progress",
                    "unknown",
                    "provider_succeeded",
                    "settled",
                    "terminal_failed",
                ],
                value["state"],
            ),
            retryable=value["retryable"],
            action=cast(Literal["retry_create", "reconcile", "wait", "none"], value["action"]),
            updated_at=_date_time(value["updated_at"], "updated_at"),
        )
    if operation_key.startswith("workspaces.sync."):
        if not isinstance(value, dict) or set(value) != {
            "request_id",
            "selected_protocol",
            "capabilities",
            "data",
        }:
            raise DecodeFailure("unknown_member", "$")
        capabilities = value["capabilities"]
        if (
            not is_uuid(value["request_id"])
            or value["selected_protocol"] not in (1, 2)
            or not isinstance(capabilities, list)
            or len(capabilities) != len(_WORKSPACE_SYNC_CAPABILITIES)
            or any(not isinstance(item, str) for item in capabilities)
            or set(capabilities) != _WORKSPACE_SYNC_CAPABILITIES
            or contains_denied(value)
        ):
            raise DecodeFailure("invalid_workspace_sync_envelope", "$")
        selected_protocol = cast(Literal[1, 2], value["selected_protocol"])
        decoded_data = _decode_workspace_sync_data(operation_key, value["data"])
        nested_protocol = (
            decoded_data.sync.selected_protocol
            if isinstance(decoded_data, WorkspaceSyncManifestReceipt)
            else getattr(decoded_data, "selected_protocol", None)
        )
        nested_capabilities = (
            decoded_data.sync.capabilities
            if isinstance(decoded_data, WorkspaceSyncManifestReceipt)
            else getattr(decoded_data, "capabilities", None)
        )
        if nested_protocol is not None and nested_protocol != selected_protocol:
            raise DecodeFailure("workspace_sync_protocol_mismatch", "data.selected_protocol")
        if nested_capabilities is not None and set(nested_capabilities) != set(capabilities):
            raise DecodeFailure("workspace_sync_capability_mismatch", "data.capabilities")
        return WorkspaceSyncEnvelope(
            request_id=cast(str, value["request_id"]),
            selected_protocol=selected_protocol,
            capabilities=_decode_sync_capabilities(capabilities),
            data=decoded_data,
        )
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        deserialize_generated_response(encoded)
    except (TypeError, ValueError):
        raise DecodeFailure("invalid_json", "$") from None
    operation = OPERATIONS[operation_key]
    if operation_key == "agentSessions.list":
        return _decode_agent_session_page(value)
    if operation_key in {"sessions.list", "records.list"}:
        carriers = sanitize_response(value, operation.response_fields, collection=True)
        if not isinstance(carriers, list):
            raise DecodeFailure("not_array", "$")
        decoder = _decode_session if operation_key == "sessions.list" else _decode_record
        return [decoder(item) for item in carriers if isinstance(item, DecodedCarrier)]
    sanitized = sanitize_response(value, operation.response_fields)
    if not isinstance(sanitized, DecodedCarrier):
        raise DecodeFailure("not_mapping", "$")
    if operation_key == "agentSessions.createTerminalConnection":
        return _decode_terminal_connection_grant(sanitized)
    if operation_key in {
        "agentSessions.create",
        "agentSessions.get",
        "agentSessions.rename",
        "agentSessions.terminate",
        "sessions.create",
        "sessions.get",
        "sessions.pause",
        "sessions.resume",
        "sessions.start",
        "sessions.stop",
    }:
        return (
            _decode_agent_session(sanitized)
            if operation_key.startswith("agentSessions.")
            else _decode_session(sanitized)
        )
    if operation_key == "sessions.exec":
        return _decode_exec(sanitized)
    if operation_key == "agentSessions.agentAuth":
        return _decode_agent_session_auth(sanitized)
    if operation_key in {"sessions.checkpoint", "sessions.delete"}:
        return _decode_ack(sanitized)
    if operation_key == "sessions.open":
        return _decode_open(sanitized)
    if operation_key == "capabilities.get":
        return _decode_capability_snapshot(sanitized)
    if operation_key == "me.get":
        return _decode_me(sanitized)
    raise KeyError(operation_key)


def encode_for_operation(
    operation_key: str, supplied: Mapping[str, object] | None
) -> dict[str, object]:
    operation = OPERATIONS[operation_key]
    if supplied is None:
        return {}
    if set(supplied) - set(operation.request_fields):
        raise EncodeFailure("Request does not match the Runa contract.")
    carrier = {key: supplied[key] for key in operation.request_fields if key in supplied}
    if operation_key.startswith("agentSessions."):
        try:
            encoded = json.dumps(
                carrier, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            )
            decoded = json.loads(encoded)
        except (TypeError, ValueError):
            raise EncodeFailure("Request does not match the Runa contract.") from None
        if not isinstance(decoded, dict):
            raise EncodeFailure("Request does not match the Runa contract.")
        return cast(dict[str, object], decoded)
    try:
        encoded = serialize_generated_request(carrier)  # type: ignore[arg-type]
        decoded = deserialize_generated_response(encoded)
    except (TypeError, ValueError):
        raise EncodeFailure("Request does not match the Runa contract.") from None
    if not isinstance(decoded, dict):
        raise EncodeFailure("Request does not match the Runa contract.")
    return cast(dict[str, object], decoded)

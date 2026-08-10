"""Public synchronous and asynchronous Runa clients."""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import threading
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from contextlib import asynccontextmanager, contextmanager
from typing import Literal, TypeVar, cast
from urllib.parse import urlencode

from runa.errors import ApiError, ConfigError
from runa.models import (
    UNSET,
    Acknowledgement,
    AgentSession,
    AgentSessionAuth,
    AgentSessionAuthMode,
    AgentSessionCreateOptions,
    AgentSessionListOptions,
    AgentSessionPage,
    CapabilityScope,
    CapabilitySnapshot,
    ExecOptions,
    ExecResult,
    MachineCreateRequest,
    Me,
    OpenSessionResult,
    OutboundPolicy,
    OutboundPolicyMode,
    Record,
    SessionAgent,
    SessionCreateOptions,
    SessionSnapshot,
    TerminalConnectionCreateOptions,
    TerminalConnectionGrant,
    WorkspaceBinding,
    WorkspaceBindingCreateRequest,
    WorkspaceBindingLookup,
    WorkspaceSyncBeginRequest,
    WorkspaceSyncChangeOptions,
    WorkspaceSyncChangePage,
    WorkspaceSyncChunkContent,
    WorkspaceSyncChunkReceipt,
    WorkspaceSyncChunkRef,
    WorkspaceSyncCommitReceipt,
    WorkspaceSyncCommitRequest,
    WorkspaceSyncEnvelope,
    WorkspaceSyncManifestEntry,
    WorkspaceSyncManifestPageRequest,
    WorkspaceSyncManifestReceipt,
    WorkspaceSyncProtocolRange,
    WorkspaceSyncReconcileReceipt,
    WorkspaceSyncReconcileRequest,
    WorkspaceSyncSession,
)

from ._internal.config import EffectiveConfig, SafeConfigFailure, resolve_config
from ._internal.constraints import is_uuid
from ._internal.contract import OPERATIONS, decode_for_operation, encode_for_operation
from ._internal.contract.bridge import DecodeFailure
from ._internal.observability import NullObserver, OperationObserver
from ._internal.resilience import run_async, run_sync
from ._internal.transport import (
    AsyncHttpTransport,
    AsyncTransport,
    PreparedRequest,
    RequestContext,
    SyncHttpTransport,
    SyncTransport,
    disposition,
    prepare_request,
    security_dispatch_guard,
)

_T = TypeVar("_T")
_OUTBOUND_HOST_RULE = re.compile(
    r"^(?:\*\.)?(?![0-9]{1,3}(?:\.[0-9]{1,3}){3}$)"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)
_AGENT_SESSION_CWD = re.compile(r"^/workspace(?:/.*)?$")
_IDEMPOTENCY_KEY = re.compile(r"^[!-~]{8,128}$")
_CLIENT_INSTANCE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")


def _config_or_raise(result: EffectiveConfig | SafeConfigFailure) -> EffectiveConfig:
    if isinstance(result, SafeConfigFailure):
        raise ConfigError() from None
    return result


def _validate_uuid(value: object) -> str:
    if not is_uuid(value):
        raise ConfigError() from None
    return cast(str, value)


def _require_matching_snapshot(snapshot: SessionSnapshot, requested_id: str) -> SessionSnapshot:
    if snapshot.id != requested_id:
        raise ApiError(200, code="malformed_response") from None
    return snapshot


def _require_matching_agent_session(value: AgentSession, requested_id: str) -> AgentSession:
    if value.id != requested_id:
        raise ApiError(200, code="malformed_response") from None
    return value


def _validate_agent_session_name(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 80:
        raise ConfigError() from None
    return value


def _validate_agent_session_create(
    options: object,
) -> tuple[dict[str, object], str]:
    if not isinstance(options, AgentSessionCreateOptions):
        raise ConfigError() from None
    if (
        not isinstance(options.agent, SessionAgent)
        or not isinstance(options.cwd, str)
        or not 10 <= len(options.cwd) <= 1024
        or _AGENT_SESSION_CWD.fullmatch(options.cwd) is None
        or not is_uuid(options.workspace_binding_id)
        or type(options.workspace_generation) is not int
        or options.workspace_generation < 1
        or not isinstance(options.idempotency_key, str)
        or _IDEMPOTENCY_KEY.fullmatch(options.idempotency_key) is None
        or (options.name is not None and not 1 <= len(options.name) <= 80)
        or (
            options.auth_mode is not None
            and not isinstance(options.auth_mode, AgentSessionAuthMode)
        )
    ):
        raise ConfigError() from None
    if options.credential_binding_id is not None:
        _validate_uuid(options.credential_binding_id)
    effective_mode = options.auth_mode or (
        AgentSessionAuthMode.CREDENTIAL_BINDING
        if options.agent is SessionAgent.OPENCLAW
        else AgentSessionAuthMode.INTERACTIVE_LOGIN
    )
    if (
        effective_mode is AgentSessionAuthMode.INTERACTIVE_LOGIN
        and options.credential_binding_id is not None
    ) or (
        effective_mode is AgentSessionAuthMode.CREDENTIAL_BINDING
        and options.credential_binding_id is None
    ):
        raise ConfigError() from None
    supplied: dict[str, object] = {
        "agent": options.agent.value,
        "cwd": options.cwd,
        "workspace_binding_id": options.workspace_binding_id,
        "workspace_generation": options.workspace_generation,
    }
    if options.name is not None:
        supplied["name"] = options.name
    if options.auth_mode is not None:
        supplied["auth_mode"] = options.auth_mode.value
    if options.credential_binding_id is not None:
        supplied["credential_binding_id"] = options.credential_binding_id
    return encode_for_operation("agentSessions.create", supplied), options.idempotency_key


def _validate_terminal_connection_create(
    options: object,
) -> tuple[dict[str, object], str]:
    if (
        not isinstance(options, TerminalConnectionCreateOptions)
        or not isinstance(options.idempotency_key, str)
        or _IDEMPOTENCY_KEY.fullmatch(options.idempotency_key) is None
        or not isinstance(options.client_instance_id, str)
        or _CLIENT_INSTANCE_ID.fullmatch(options.client_instance_id) is None
    ):
        raise ConfigError() from None
    supplied: dict[str, object] = {
        "protocol": "runa.terminal.v1",
        "client_instance_id": options.client_instance_id,
    }
    if options.resume_handle is not None:
        supplied["resume_handle"] = _validate_uuid(options.resume_handle)
    return (
        encode_for_operation("agentSessions.createTerminalConnection", supplied),
        options.idempotency_key,
    )


def _agent_session_query(options: object) -> dict[str, str]:
    if not isinstance(options, AgentSessionListOptions):
        raise ConfigError() from None
    query: dict[str, str] = {}
    if options.limit is not None:
        if type(options.limit) is not int or not 1 <= options.limit <= 100:
            raise ConfigError() from None
        query["limit"] = str(options.limit)
    if options.cursor is not None:
        if not isinstance(options.cursor, str) or not 1 <= len(options.cursor) <= 512:
            raise ConfigError() from None
        query["cursor"] = options.cursor
    return query


def _capability_query(scope: object, resource_id: object) -> dict[str, str]:
    if not isinstance(scope, CapabilityScope):
        raise ConfigError() from None
    if scope is CapabilityScope.ACCOUNT:
        if resource_id is not None:
            raise ConfigError() from None
        return {"scope": scope.value}
    return {"scope": scope.value, "resource_id": _validate_uuid(resource_id)}


def _validate_capability_response(
    value: object,
    headers: Mapping[str, str],
) -> object:
    if not isinstance(value, CapabilitySnapshot):
        raise ApiError(200, code="malformed_response") from None
    etag = next((item for key, item in headers.items() if key.lower() == "etag"), None)
    if etag != f'"{value.etag}"':
        raise ApiError(200, code="malformed_response") from None
    return value


def _validate_agent_auth_headers(value: object, headers: Mapping[str, str]) -> object:
    if not isinstance(value, AgentSessionAuth):
        raise ApiError(200, code="malformed_response") from None
    cache_control = next(
        (item for key, item in headers.items() if key.lower() == "cache-control"), None
    )
    if cache_control is None or cache_control.strip().lower() != "no-store":
        raise ApiError(200, code="malformed_response") from None
    return value


def _validate_create(name: object, options: object) -> tuple[str, SessionCreateOptions]:
    if not isinstance(name, str) or not 1 <= len(name) <= 80:
        raise ConfigError() from None
    if not isinstance(options, SessionCreateOptions):
        raise ConfigError() from None
    if options.idempotency_key is not None and (
        not isinstance(options.idempotency_key, str)
        or _IDEMPOTENCY_KEY.fullmatch(options.idempotency_key) is None
    ):
        raise ConfigError() from None
    if options.agent is not UNSET and not isinstance(options.agent, SessionAgent):
        raise ConfigError() from None
    for value, minimum, maximum in (
        (options.vcpus, 1, 8),
        (options.memory_mib, 512, 16384),
        (options.runtime_port, 1, 65535),
    ):
        if value is not UNSET and (type(value) is not int or not minimum <= value <= maximum):
            raise ConfigError() from None
    if options.allowed_hosts is not UNSET and (
        type(options.allowed_hosts) is not list
        or len(options.allowed_hosts) > 128
        or any(type(host) is not str or not host for host in options.allowed_hosts)
    ):
        raise ConfigError() from None
    if options.allowed_hosts is not UNSET and options.outbound_policy is not UNSET:
        raise ConfigError() from None
    if options.outbound_policy is not UNSET:
        policy = options.outbound_policy
        if (
            not isinstance(policy, OutboundPolicy)
            or not isinstance(policy.mode, OutboundPolicyMode)
            or type(policy.hosts) is not list
            or len(policy.hosts) > 128
            or len(set(policy.hosts)) != len(policy.hosts)
            or any(
                type(host) is not str
                or not 3 <= len(host) <= 253
                or _OUTBOUND_HOST_RULE.fullmatch(host) is None
                for host in policy.hosts
            )
        ):
            raise ConfigError() from None
    return name, options


def _create_body(name: str, options: SessionCreateOptions) -> dict[str, object]:
    supplied: dict[str, object] = {"name": name}
    for key in (
        "agent",
        "vcpus",
        "memory_mib",
        "allowed_hosts",
        "outbound_policy",
        "runtime_port",
    ):
        value = getattr(options, key)
        if value is not UNSET:
            if key == "agent" and hasattr(value, "value"):
                supplied[key] = value.value
            elif key == "allowed_hosts":
                supplied[key] = list(value)
            elif key == "outbound_policy":
                supplied[key] = {"mode": value.mode.value, "hosts": list(value.hosts)}
            else:
                supplied[key] = value
    return encode_for_operation("sessions.create", supplied)


def _session_create_key(options: SessionCreateOptions) -> str:
    return options.idempotency_key or f"runa_sdk_{secrets.token_urlsafe(18)}"


def _exec_body(
    command: str | Sequence[str], options: ExecOptions
) -> tuple[dict[str, object], int | None]:
    if not isinstance(options, ExecOptions):
        raise ConfigError() from None
    if isinstance(command, str):
        if not command:
            raise ConfigError() from None
        normalized_command = command
        args: list[str] | None = None
    elif isinstance(command, Sequence) and not isinstance(command, bytes | bytearray | memoryview):
        if len(command) == 0 or any(not isinstance(item, str) for item in command):
            raise ConfigError() from None
        normalized_command = command[0]
        if not normalized_command:
            raise ConfigError() from None
        args = list(command[1:])
    else:
        raise ConfigError() from None

    supplied: dict[str, object] = {"command": normalized_command}
    if args is not None:
        supplied["args"] = args
    if options.cwd is not UNSET:
        if not isinstance(options.cwd, str):
            raise ConfigError() from None
        supplied["cwd"] = options.cwd
    timeout: int | None = None
    if options.timeout_secs is not UNSET:
        if type(options.timeout_secs) is not int or not 1 <= options.timeout_secs <= 600:
            raise ConfigError() from None
        timeout = options.timeout_secs
        supplied["timeout_secs"] = timeout
    return encode_for_operation("sessions.exec", supplied), timeout


_SESSIONS_MANAGER_TOKEN = object()
_AGENT_SESSIONS_MANAGER_TOKEN = object()
_CAPABILITIES_MANAGER_TOKEN = object()
_RECORDS_MANAGER_TOKEN = object()
_SESSION_TOKEN = object()
_ASYNC_SESSIONS_MANAGER_TOKEN = object()
_ASYNC_AGENT_SESSIONS_MANAGER_TOKEN = object()
_ASYNC_CAPABILITIES_MANAGER_TOKEN = object()
_ASYNC_RECORDS_MANAGER_TOKEN = object()
_ASYNC_SESSION_TOKEN = object()
_WORKSPACE_SYNC_MANAGER_TOKEN = object()
_ASYNC_WORKSPACE_SYNC_MANAGER_TOKEN = object()
_WORKSPACE_BINDINGS_MANAGER_TOKEN = object()
_ASYNC_WORKSPACE_BINDINGS_MANAGER_TOKEN = object()
_MACHINE_CREATES_MANAGER_TOKEN = object()
_ASYNC_MACHINE_CREATES_MANAGER_TOKEN = object()


def _workspace_sync_key(value: object) -> str:
    if not isinstance(value, str) or _IDEMPOTENCY_KEY.fullmatch(value) is None:
        raise ConfigError() from None
    return value


def _workspace_digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ConfigError() from None
    return value


def _workspace_protocol(value: object) -> dict[str, int]:
    if (
        not isinstance(value, WorkspaceSyncProtocolRange)
        or type(value.minimum) is not int
        or type(value.maximum) is not int
        or value.minimum < 1
        or value.maximum < value.minimum
    ):
        raise ConfigError() from None
    return {"minimum": value.minimum, "maximum": value.maximum}


def _positive_int(value: object, *, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ConfigError() from None
    return value


def _manifest_entry(value: object) -> dict[str, object]:
    if (
        not isinstance(value, WorkspaceSyncManifestEntry)
        or not isinstance(value.path, str)
        or not 1 <= len(value.path) <= 4096
        or value.kind not in {"directory", "file", "symlink"}
        or type(value.executable) is not bool
        or (
            value.link_target is not None
            and (not isinstance(value.link_target, str) or len(value.link_target) > 4096)
        )
        or not isinstance(value.chunks, list)
        or len(value.chunks) > 4096
    ):
        raise ConfigError() from None
    chunks: list[dict[str, object]] = []
    for chunk in value.chunks:
        if not isinstance(chunk, WorkspaceSyncChunkRef):
            raise ConfigError() from None
        chunks.append(
            {
                "digest": _workspace_digest(chunk.digest),
                "byte_length": _positive_int(chunk.byte_length, maximum=8_388_608),
            }
        )
    return {
        "path": value.path,
        "kind": value.kind,
        "byte_length": _positive_int(value.byte_length),
        "executable": value.executable,
        "chunks": chunks,
        "link_target": value.link_target,
    }


def _binding_identity(value: object) -> dict[str, str]:
    if not isinstance(value, WorkspaceBindingCreateRequest | WorkspaceBindingLookup):
        raise ConfigError() from None
    return {
        "workspace_id": _validate_uuid(value.workspace_id),
        "project_id": _validate_uuid(value.project_id),
        "local_instance_id": _validate_uuid(value.local_instance_id),
        "machine_id": _validate_uuid(value.machine_id),
        "exclusion_policy_digest": _workspace_digest(value.exclusion_policy_digest),
    }


def _binding_create_body(value: object) -> dict[str, object]:
    identity = _binding_identity(value)
    if not isinstance(value, WorkspaceBindingCreateRequest):
        raise ConfigError() from None
    prefixes = value.excluded_prefixes
    if (
        not isinstance(prefixes, list)
        or len(prefixes) > 10_000
        or len(prefixes) != len(set(prefixes))
        or any(
            not isinstance(prefix, str)
            or not 1 <= len(prefix) <= 4096
            or prefix.startswith(("/", "\\"))
            or "\\" in prefix
            or any(ord(character) < 32 or ord(character) == 127 for character in prefix)
            or any(part in {"", ".", ".."} for part in prefix.split("/"))
            for prefix in prefixes
        )
    ):
        raise ConfigError() from None
    return {**identity, "excluded_prefixes": list(prefixes)}


def _require_binding_matches(
    value: WorkspaceBinding,
    identity: WorkspaceBindingCreateRequest | WorkspaceBindingLookup,
    *,
    binding_id: str | None = None,
) -> WorkspaceBinding:
    if (
        (binding_id is not None and value.binding_id != binding_id)
        or value.workspace_id != identity.workspace_id
        or value.project_id != identity.project_id
        or value.local_instance_id != identity.local_instance_id
        or value.machine_id != identity.machine_id
        or value.exclusion_policy_digest != identity.exclusion_policy_digest
    ):
        raise ApiError(200, code="malformed_response") from None
    return value


def _workspace_sync_body(value: object) -> dict[str, object]:
    if isinstance(value, WorkspaceSyncBeginRequest):
        return {
            "workspace_binding_id": _validate_uuid(value.workspace_binding_id),
            "machine_id": _validate_uuid(value.machine_id),
            "base_generation": _positive_int(value.base_generation),
            "exclusion_policy_digest": _workspace_digest(value.exclusion_policy_digest),
            "protocol": _workspace_protocol(value.protocol),
            "minimum_reader": _positive_int(value.minimum_reader, minimum=1),
            "minimum_writer": _positive_int(value.minimum_writer, minimum=1),
        }
    if isinstance(value, WorkspaceSyncManifestPageRequest):
        if (
            type(value.is_last) is not bool
            or not isinstance(value.entries, list)
            or len(value.entries) > 4096
        ):
            raise ConfigError() from None
        return {
            "page_index": _positive_int(value.page_index, maximum=255),
            "is_last": value.is_last,
            "minimum_reader": _positive_int(value.minimum_reader, minimum=1),
            "minimum_writer": _positive_int(value.minimum_writer, minimum=1),
            "entries": [_manifest_entry(item) for item in value.entries],
        }
    if isinstance(value, WorkspaceSyncCommitRequest):
        return {
            "expected_generation": _positive_int(value.expected_generation),
            "exclusion_policy_digest": _workspace_digest(value.exclusion_policy_digest),
            "manifest_root": _workspace_digest(value.manifest_root),
            "minimum_reader": _positive_int(value.minimum_reader, minimum=1),
            "minimum_writer": _positive_int(value.minimum_writer, minimum=1),
        }
    if isinstance(value, WorkspaceSyncReconcileRequest):
        return {
            "workspace_binding_id": _validate_uuid(value.workspace_binding_id),
            "machine_id": _validate_uuid(value.machine_id),
            "observed_generation": _positive_int(value.observed_generation),
            "exclusion_policy_digest": _workspace_digest(value.exclusion_policy_digest),
            "manifest_root": _workspace_digest(value.manifest_root),
            "protocol": _workspace_protocol(value.protocol),
        }
    raise ConfigError() from None


def _workspace_sync_query(value: object) -> dict[str, str]:
    if (
        not isinstance(value, WorkspaceSyncChangeOptions)
        or type(value.reader_version) is not int
        or value.reader_version < 1
        or (
            value.limit is not None
            and (type(value.limit) is not int or not 1 <= value.limit <= 1000)
        )
        or (
            value.cursor is not None
            and (not isinstance(value.cursor, str) or not 1 <= len(value.cursor) <= 1024)
        )
    ):
        raise ConfigError() from None
    return {
        "reader_version": str(value.reader_version),
        **({} if value.cursor is None else {"cursor": value.cursor}),
        **({} if value.limit is None else {"limit": str(value.limit)}),
    }


class WorkspaceBindingsManager:
    """Create, adopt, and resolve canonical workspace bindings."""

    __slots__ = ("_client",)

    def __init__(self, client: Runa, token: object = None) -> None:
        if token is not _WORKSPACE_BINDINGS_MANAGER_TOKEN:
            raise TypeError("WorkspaceBindingsManager cannot be constructed directly.")
        self._client = client

    def create(
        self, request: WorkspaceBindingCreateRequest, idempotency_key: str
    ) -> WorkspaceBinding:
        """Create or exactly adopt one canonical workspace binding."""

        value = cast(
            WorkspaceBinding,
            self._client._invoke(
                "workspaceBindings.create",
                body=_binding_create_body(request),
                idempotency_key=_workspace_sync_key(idempotency_key),
            ),
        )
        return _require_binding_matches(value, request)

    def get(self, binding_id: str, identity: WorkspaceBindingLookup) -> WorkspaceBinding:
        """Get one canonical binding using its complete authenticated identity."""

        clean_binding_id = _validate_uuid(binding_id)
        if clean_binding_id == identity.workspace_id:
            raise ConfigError() from None
        value = cast(
            WorkspaceBinding,
            self._client._invoke(
                "workspaceBindings.get",
                path_values={"binding_id": clean_binding_id},
                query_values=_binding_identity(identity),
            ),
        )
        return _require_binding_matches(value, identity, binding_id=clean_binding_id)


class WorkspaceSyncManager:
    """Explicit bounded workspace synchronization operations."""

    __slots__ = ("_client",)

    def __init__(self, client: Runa, token: object = None) -> None:
        if token is not _WORKSPACE_SYNC_MANAGER_TOKEN:
            raise TypeError("WorkspaceSyncManager cannot be constructed directly.")
        self._client = client

    def _mutation(
        self, operation: str, resource_id: str, request: object, key: str
    ) -> WorkspaceSyncEnvelope[object]:
        return cast(
            WorkspaceSyncEnvelope[object],
            self._client._invoke(
                operation,
                path_values={"id": _validate_uuid(resource_id)},
                body=_workspace_sync_body(request),
                idempotency_key=_workspace_sync_key(key),
            ),
        )

    def begin(
        self, workspace_id: str, request: WorkspaceSyncBeginRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncSession]:
        """Begin one bounded workspace synchronization session."""

        if _validate_uuid(workspace_id) == request.workspace_binding_id:
            raise ConfigError() from None
        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncSession],
            self._mutation("workspaces.sync.begin", workspace_id, request, idempotency_key),
        )

    def negotiate(
        self, sync_id: str, request: WorkspaceSyncManifestPageRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]:
        """Negotiate one ordered manifest page."""

        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt],
            self._mutation("workspaces.sync.negotiate", sync_id, request, idempotency_key),
        )

    def upload_chunk(
        self, sync_id: str, digest: str, data: bytes, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]:
        """Upload one content-addressed workspace chunk."""

        if (
            re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(data, bytes)
            or len(data) > 8_388_608
        ):
            raise ConfigError() from None
        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt],
            self._client._invoke(
                "workspaces.sync.chunk",
                path_values={"id": _validate_uuid(sync_id), "digest": digest},
                raw_body=bytes(data),
                idempotency_key=_workspace_sync_key(idempotency_key),
            ),
        )

    def download_chunk(self, sync_id: str, digest: str) -> bytes:
        """Download one chunk as bytes after strict digest and length verification."""

        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ConfigError() from None
        envelope = cast(
            WorkspaceSyncEnvelope[WorkspaceSyncChunkContent],
            self._client._invoke(
                "workspaces.sync.chunkDownload",
                path_values={"id": _validate_uuid(sync_id), "digest": digest},
            ),
        )
        if envelope.data.digest != digest or envelope.data.minimum_reader > 2:
            raise ApiError(200, code="malformed_response") from None
        return bytes(envelope.data.content)

    def commit(
        self, sync_id: str, request: WorkspaceSyncCommitRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]:
        """Commit one complete synchronized workspace generation."""

        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt],
            self._mutation("workspaces.sync.commit", sync_id, request, idempotency_key),
        )

    def changes(
        self, sync_id: str, options: WorkspaceSyncChangeOptions
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncChangePage]:
        """Read one ordered page of committed workspace changes."""

        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncChangePage],
            self._client._invoke(
                "workspaces.sync.changes",
                path_values={"id": _validate_uuid(sync_id)},
                query_values=_workspace_sync_query(options),
            ),
        )

    def reconcile(
        self, workspace_id: str, request: WorkspaceSyncReconcileRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]:
        """Reconcile one workspace against an observed local generation."""

        if _validate_uuid(workspace_id) == request.workspace_binding_id:
            raise ConfigError() from None
        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt],
            self._mutation("workspaces.sync.reconcile", workspace_id, request, idempotency_key),
        )


class MachineCreatesManager:
    """Non-secret machine-create status and exact-name reconciliation."""

    __slots__ = ("_client",)

    def __init__(self, client: Runa, token: object = None) -> None:
        if token is not _MACHINE_CREATES_MANAGER_TOKEN:
            raise TypeError("MachineCreatesManager cannot be constructed directly.")
        self._client = client

    def get(self, request_id: str) -> MachineCreateRequest:
        """Get one non-secret machine-create request state."""

        return cast(
            MachineCreateRequest,
            self._client._invoke(
                "machineCreates.get", path_values={"id": _validate_uuid(request_id)}
            ),
        )

    def reconcile(self, request_id: str) -> MachineCreateRequest:
        """Reconcile one exact machine-create request state."""

        return cast(
            MachineCreateRequest,
            self._client._invoke(
                "machineCreates.reconcile", path_values={"id": _validate_uuid(request_id)}
            ),
        )


class SessionsManager:
    """Stable synchronous session manager obtained from ``Runa.sessions``.

    Direct construction is unsupported and raises ``TypeError``.
    """

    __slots__ = ("_client",)

    def __init__(self, client: Runa, token: object = None) -> None:
        if token is not _SESSIONS_MANAGER_TOKEN:
            raise TypeError("SessionsManager cannot be constructed directly.")
        self._client = client

    def create(self, name: str, options: SessionCreateOptions) -> Session:
        """Create one session.

        Args:
            name: Human-readable name of 1-80 characters.
            options: Explicit omission-aware creation options.
        Returns:
            A client-owned session handle.
        Raises:
            ConfigError: If an input violates the local contract.
            ApiError: If the request fails or the response is malformed.
        Examples:
            See ``REF-EX-SESSIONSMANAGER`` and ``TC-091-09``.
        """
        clean_name, clean_options = _validate_create(name, options)
        snapshot = cast(
            SessionSnapshot,
            self._client._invoke(
                "sessions.create",
                body=_create_body(clean_name, clean_options),
                idempotency_key=_session_create_key(clean_options),
            ),
        )
        return Session(self, snapshot, _SESSION_TOKEN)

    def list(self) -> list[Session]:
        """List visible sessions.

        Returns:
            New client-owned handles in service order.
        Raises:
            ApiError: If the request fails or the response is malformed.
        Examples:
            See ``REF-EX-SESSIONSMANAGER`` and ``TC-091-09``.
        """
        snapshots = cast(list[SessionSnapshot], self._client._invoke("sessions.list"))
        return [Session(self, item, _SESSION_TOKEN) for item in snapshots]

    def get(self, session_id: str) -> Session:
        """Retrieve one session.

        Args:
            session_id: Canonical lowercase session UUID.
        Returns:
            A client-owned handle whose ID matches ``session_id``.
        Raises:
            ConfigError: If ``session_id`` is not canonical.
            ApiError: If the request fails, is missing, or is malformed.
        Examples:
            See ``REF-EX-SESSIONSMANAGER`` and ``TC-091-09``.
        """
        clean_id = _validate_uuid(session_id)
        snapshot = cast(
            SessionSnapshot, self._client._invoke("sessions.get", path_values={"id": clean_id})
        )
        return Session(self, _require_matching_snapshot(snapshot, clean_id), _SESSION_TOKEN)

    def _lifecycle(self, handle: Session, action: str) -> Session:
        snapshot = cast(
            SessionSnapshot,
            self._client._invoke(f"sessions.{action}", path_values={"id": handle.id}),
        )
        handle._replace(_require_matching_snapshot(snapshot, handle.id))
        return handle

    def _delete(self, handle: Session) -> Acknowledgement:
        return cast(
            Acknowledgement,
            self._client._invoke("sessions.delete", path_values={"id": handle.id}),
        )

    def _exec(
        self, handle: Session, command: str | Sequence[str], options: ExecOptions
    ) -> ExecResult:
        body, timeout_secs = _exec_body(command, options)
        return cast(
            ExecResult,
            self._client._invoke(
                "sessions.exec",
                path_values={"id": handle.id},
                body=body,
                exec_timeout_secs=timeout_secs,
            ),
        )

    def _checkpoint(self, handle: Session, name: str) -> Acknowledgement:
        if not isinstance(name, str) or not 1 <= len(name) <= 80:
            raise ConfigError() from None
        return cast(
            Acknowledgement,
            self._client._invoke(
                "sessions.checkpoint",
                path_values={"id": handle.id},
                body=encode_for_operation("sessions.checkpoint", {"name": name}),
            ),
        )

    def _open(self, handle: Session) -> OpenSessionResult:
        return cast(
            OpenSessionResult,
            self._client._invoke("sessions.open", path_values={"id": handle.id}),
        )


class AgentSessionsManager:
    """Stable synchronous manager for processes owned by one Runa machine."""

    __slots__ = ("_client",)

    def __init__(self, client: Runa, token: object = None) -> None:
        if token is not _AGENT_SESSIONS_MANAGER_TOKEN:
            raise TypeError("AgentSessionsManager cannot be constructed directly.")
        self._client = client

    def list(
        self,
        machine_id: str,
        options: AgentSessionListOptions | None = None,
    ) -> AgentSessionPage:
        """Return one bounded page for an owned machine."""

        clean_machine_id = _validate_uuid(machine_id)
        page = cast(
            AgentSessionPage,
            self._client._invoke(
                "agentSessions.list",
                path_values={"id": clean_machine_id},
                query_values=_agent_session_query(options or AgentSessionListOptions()),
            ),
        )
        if any(item.machine_id != clean_machine_id for item in page.items):
            raise ApiError(200, code="malformed_response") from None
        return page

    def create(self, machine_id: str, options: AgentSessionCreateOptions) -> AgentSession:
        """Create one durable AgentSession launch intent."""

        clean_machine_id = _validate_uuid(machine_id)
        body, idempotency_key = _validate_agent_session_create(options)
        created = cast(
            AgentSession,
            self._client._invoke(
                "agentSessions.create",
                path_values={"id": clean_machine_id},
                body=body,
                idempotency_key=idempotency_key,
            ),
        )
        if (
            created.machine_id != clean_machine_id
            or created.agent is not options.agent
            or created.cwd != options.cwd
            or created.workspace_binding_id != options.workspace_binding_id
            or created.workspace_generation != options.workspace_generation
        ):
            raise ApiError(201, code="malformed_response") from None
        return created

    def get(self, agent_session_id: str) -> AgentSession:
        """Get one AgentSession by its opaque canonical UUID."""

        return self._one("agentSessions.get", agent_session_id)

    def agent_auth(self, agent_session: AgentSession) -> AgentSessionAuth:
        """Read fresh auth evidence bound to an already admitted AgentSession."""

        if not isinstance(agent_session, AgentSession):
            raise ConfigError() from None
        value = cast(
            AgentSessionAuth,
            self._client._invoke("agentSessions.agentAuth", path_values={"id": agent_session.id}),
        )
        if (
            value.agent_session_id != agent_session.id
            or value.auth_mode is not agent_session.auth_mode
            or value.process_epoch != agent_session.process_epoch
        ):
            raise ApiError(200, code="malformed_response") from None
        return value

    def rename(self, agent_session_id: str, name: str) -> AgentSession:
        """Rename metadata without changing process facts."""

        clean_name = _validate_agent_session_name(name)
        value = self._one(
            "agentSessions.rename",
            agent_session_id,
            encode_for_operation("agentSessions.rename", {"name": clean_name}),
        )
        if value.name != clean_name:
            raise ApiError(200, code="malformed_response") from None
        return value

    def terminate(self, agent_session_id: str) -> AgentSession:
        """Request durable termination without asserting process absence."""

        return self._one("agentSessions.terminate", agent_session_id)

    def create_terminal_connection(
        self,
        agent_session_id: str,
        options: TerminalConnectionCreateOptions,
    ) -> TerminalConnectionGrant:
        """Create terminal connection metadata without opening or consuming the stream."""

        clean_id = _validate_uuid(agent_session_id)
        body, idempotency_key = _validate_terminal_connection_create(options)
        return cast(
            TerminalConnectionGrant,
            self._client._invoke(
                "agentSessions.createTerminalConnection",
                path_values={"id": clean_id},
                body=body,
                idempotency_key=idempotency_key,
            ),
        )

    def _one(
        self,
        operation_key: str,
        agent_session_id: str,
        body: Mapping[str, object] | None = None,
        raw_body: bytes | None = None,
    ) -> AgentSession:
        clean_id = _validate_uuid(agent_session_id)
        value = cast(
            AgentSession,
            self._client._invoke(
                operation_key,
                path_values={"id": clean_id},
                body=body,
                raw_body=raw_body,
            ),
        )
        return _require_matching_agent_session(value, clean_id)


class CapabilitiesManager:
    """Stable synchronous capability discovery manager.

    Examples:
        See ``REF-EX-CAPABILITIESMANAGER`` and ``TC-091-09``.
    """

    __slots__ = ("_client",)

    def __init__(self, client: Runa, token: object = None) -> None:
        if token is not _CAPABILITIES_MANAGER_TOKEN:
            raise TypeError("CapabilitiesManager cannot be constructed directly.")
        self._client = client

    def get(
        self,
        scope: CapabilityScope,
        resource_id: str | None = None,
    ) -> CapabilitySnapshot:
        """Get leased availability evidence without granting authority.

        Args:
            scope: Account, machine, or explicit AgentSession scope.
            resource_id: Required machine or AgentSession UUID; absent for account scope.
        Returns:
            A fresh account, machine, or AgentSession capability snapshot.
        Raises:
            ConfigError: If the scope and resource identifier do not form a valid request.
            ApiError: If discovery fails or the response is malformed.
        Examples:
            See ``REF-EX-CAPABILITIESMANAGER`` and ``TC-091-09``.
        """

        query = _capability_query(scope, resource_id)
        snapshot = cast(
            CapabilitySnapshot,
            self._client._invoke("capabilities.get", query_values=query),
        )
        if snapshot.subject_scope is not scope or (
            scope is not CapabilityScope.ACCOUNT and snapshot.subject_id != resource_id
        ):
            raise ApiError(200, code="malformed_response") from None
        return snapshot


class RecordsManager:
    """Stable synchronous records manager; obtain from :attr:`Runa.records`."""

    __slots__ = ("_client",)

    def __init__(self, client: Runa, token: object = None) -> None:
        if token is not _RECORDS_MANAGER_TOKEN:
            raise TypeError("RecordsManager cannot be constructed directly.")
        self._client = client

    def list(self) -> list[Record]:
        """List visible records.

        Returns:
            Immutable records in service order.
        Raises:
            ApiError: If the request fails or the response is malformed.
        Examples:
            See ``REF-EX-RECORDSMANAGER`` and ``TC-091-09``.
        """
        return cast(list[Record], self._client._invoke("records.list"))


class Session:
    """Client-owned synchronous session handle.

    Obtain instances from ``Runa.sessions``; direct construction raises ``TypeError``.
    """

    __slots__ = ("_lock", "_manager", "_snapshot")

    def __init__(
        self, manager: SessionsManager, snapshot: SessionSnapshot, token: object = None
    ) -> None:
        if token is not _SESSION_TOKEN:
            raise TypeError("Session cannot be constructed directly.")
        self._manager = manager
        self._snapshot = snapshot
        self._lock = threading.Lock()

    @property
    def id(self) -> str:
        """Return the canonical session UUID.

        Returns:
            The immutable identifier from the current snapshot.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self.snapshot.id

    @property
    def snapshot(self) -> SessionSnapshot:
        """Return the latest immutable snapshot.

        Returns:
            The snapshot retained by this handle.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        with self._lock:
            return self._snapshot

    def _replace(self, snapshot: SessionSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def refresh(self) -> Session:
        """Refresh this handle from the service.

        Returns:
            This same handle after replacing its snapshot.
        Raises:
            ApiError: If the request fails or the response ID is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        refreshed = self._manager.get(self.id)
        if refreshed.id != self.id:
            raise ApiError(200, code="malformed_response")
        self._replace(refreshed.snapshot)
        return self

    def start(self) -> Session:
        """Start this session.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._lifecycle(self, "start")

    def pause(self) -> Session:
        """Pause this session.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._lifecycle(self, "pause")

    def resume(self) -> Session:
        """Resume this session.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._lifecycle(self, "resume")

    def stop(self) -> Session:
        """Stop this session.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._lifecycle(self, "stop")

    def delete(self) -> Acknowledgement:
        """Delete this session.

        Returns:
            A successful acknowledgement.
        Raises:
            ApiError: If deletion fails or the response is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._delete(self)

    def exec(
        self,
        command: str | Sequence[str],
        options: ExecOptions = ExecOptions(),  # noqa: B008
    ) -> ExecResult:
        """Execute a command in this session.

        Args:
            command: Non-empty command string or non-empty argument sequence.
            options: Working directory and 1-600 second timeout options.
        Returns:
            Captured exit status, output, truncation flags, and duration.
        Raises:
            ConfigError: If the command or options violate the local contract.
            ApiError: If execution fails or the response is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._exec(self, command, options)

    def checkpoint(self, name: str) -> Acknowledgement:
        """Create a named checkpoint.

        Args:
            name: Human-readable checkpoint name of 1-80 characters.
        Returns:
            A successful acknowledgement.
        Raises:
            ConfigError: If ``name`` violates the local contract.
            ApiError: If the request fails or the response is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._checkpoint(self, name)

    def open(self) -> OpenSessionResult:
        """Request a new session capability URL.

        Returns:
            A sensitive result that must be assigned and never logged or displayed.
        Raises:
            ApiError: If the request fails or the response is malformed.
        Examples:
            See ``REF-EX-SESSION`` and ``TC-091-09``.
        """
        return self._manager._open(self)


class Runa:
    """Synchronous root client.

    Args:
        api_key: Explicit API key, otherwise resolved from accepted configuration.
        base_url: Optional explicit Cuna API origin. ``https://api.getcuna.com`` is canonical;
            ``https://api.runacode.io`` remains accepted for compatibility.
        config_file: Explicit configuration file path.
        transport: Advanced synchronous transport override.
        diagnostic_sink: Optional disclosure-safe diagnostic sink.
        trace_sink: Optional disclosure-safe trace sink.
    Raises:
        ConfigError: If effective configuration is invalid.
    Examples:
        See ``REF-EX-RUNA`` and ``TC-091-09``.
    """

    __slots__ = (
        "_admitted",
        "_agent_sessions",
        "_capabilities",
        "_condition",
        "_config",
        "_diagnostic_sink",
        "_machine_creates",
        "_owned_transport",
        "_records",
        "_sessions",
        "_state",
        "_trace_sink",
        "_transport",
        "_workspace_bindings",
        "_workspace_sync",
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        config_file: str | os.PathLike[str] | None = None,
        transport: SyncTransport | None = None,
        diagnostic_sink: object | None = None,
        trace_sink: object | None = None,
    ) -> None:
        self._config = _config_or_raise(
            resolve_config(api_key=api_key, base_url=base_url, config_file=config_file)
        )
        self._condition = threading.Condition(threading.RLock())
        self._state = "OPEN"
        self._admitted = 0
        self._diagnostic_sink = diagnostic_sink
        self._trace_sink = trace_sink
        if transport is None:
            owned = SyncHttpTransport(self._config.base_url)
            self._owned_transport: SyncHttpTransport | None = owned
            self._transport: SyncTransport = owned
        else:
            self._owned_transport = None
            self._transport = transport
        self._sessions = SessionsManager(self, _SESSIONS_MANAGER_TOKEN)
        self._agent_sessions = AgentSessionsManager(self, _AGENT_SESSIONS_MANAGER_TOKEN)
        self._capabilities = CapabilitiesManager(self, _CAPABILITIES_MANAGER_TOKEN)
        self._records = RecordsManager(self, _RECORDS_MANAGER_TOKEN)
        self._workspace_sync = WorkspaceSyncManager(self, _WORKSPACE_SYNC_MANAGER_TOKEN)
        self._workspace_bindings = WorkspaceBindingsManager(self, _WORKSPACE_BINDINGS_MANAGER_TOKEN)
        self._machine_creates = MachineCreatesManager(self, _MACHINE_CREATES_MANAGER_TOKEN)

    @property
    def sessions(self) -> SessionsManager:
        """Return the stable sessions manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        return self._sessions

    @property
    def agent_sessions(self) -> AgentSessionsManager:
        """Return the stable AgentSession manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """

        return self._agent_sessions

    @property
    def capabilities(self) -> CapabilitiesManager:
        """Return the stable capability discovery manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """

        return self._capabilities

    @property
    def records(self) -> RecordsManager:
        """Return the stable records manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        return self._records

    @property
    def workspace_sync(self) -> WorkspaceSyncManager:
        """Return the stable explicit workspace synchronization manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        return self._workspace_sync

    @property
    def workspace_bindings(self) -> WorkspaceBindingsManager:
        """Return canonical workspace binding operations.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        return self._workspace_bindings

    @property
    def machine_creates(self) -> MachineCreatesManager:
        """Return non-secret machine-create recovery operations.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        return self._machine_creates

    @contextmanager
    def _lease(self) -> Iterator[None]:
        with self._condition:
            if self._state != "OPEN":
                raise RuntimeError("Runa client is closed.")
            self._admitted += 1
        try:
            yield
        finally:
            with self._condition:
                self._admitted -= 1
                self._condition.notify_all()

    def _invoke(
        self,
        operation_key: str,
        *,
        path_values: Mapping[str, str] | None = None,
        query_values: Mapping[str, str] | None = None,
        body: Mapping[str, object] | None = None,
        raw_body: bytes | None = None,
        idempotency_key: str | None = None,
        exec_timeout_secs: int | None = None,
    ) -> object:
        with self._lease():
            operation = OPERATIONS[operation_key]
            path = operation.path_template
            for key, value in (path_values or {}).items():
                path = path.replace(":" + key, value)
            if query_values:
                path += "?" + urlencode(query_values)
            prepared = prepare_request(
                operation_key=operation.key,
                method=operation.method,
                origin=self._config.base_url,
                relative_path=path,
                api_key=self._config.api_key,
                body=body,
                raw_body=raw_body,
                idempotency_key=idempotency_key,
                timeout_seconds=0,
            )
            observer: OperationObserver | NullObserver
            observer = (
                NullObserver()
                if self._diagnostic_sink is None and self._trace_sink is None
                else OperationObserver(operation, self._diagnostic_sink, self._trace_sink)
            )
            context = RequestContext(operation.key, observer.request_id, lambda: False)

            def execute_attempt(timeout: float) -> object:
                attempt_request = PreparedRequest(
                    prepared.operation_key,
                    prepared.method,
                    prepared.origin,
                    prepared.relative_path,
                    prepared.headers,
                    prepared.body,
                    prepared.body_bytes,
                    timeout,
                )
                security_dispatch_guard(
                    attempt_request,
                    context,
                    expected_origin=self._config.base_url,
                    expected_operation_key=operation.key,
                    expected_method=operation.method,
                    expected_path=path,
                )
                raw = self._transport(attempt_request, context)
                value = disposition(raw, operation.success_status)
                try:
                    decoded = decode_for_operation(operation_key, value)
                    if operation_key == "capabilities.get":
                        return _validate_capability_response(decoded, raw.headers)
                    if operation_key == "agentSessions.agentAuth":
                        return _validate_agent_auth_headers(decoded, raw.headers)
                    return decoded
                except DecodeFailure:
                    raise ApiError(raw.status, code="malformed_response") from None

            try:
                result = run_sync(
                    operation_key,
                    execute_attempt,
                    observer,
                    timeout_secs=exec_timeout_secs,
                )
                observer.end("success")
                return result
            except BaseException as error:
                observer.end("error", error)
                raise

    def me(self) -> Me:
        """Read the authenticated account.

        Returns:
            Account identity and workspace assignment.
        Raises:
            ApiError: If the request fails or the response is malformed.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        return cast(Me, self._invoke("me.get"))

    def close(self) -> None:
        """Close client-owned resources.

        Returns:
            ``None`` after all admitted operations and owned transport close.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        leader = False
        with self._condition:
            if self._state == "OPEN":
                self._state = "CLOSING"
                leader = True
            while not leader and self._state != "CLOSED":
                self._condition.wait()
            if not leader:
                return
            while self._admitted:
                self._condition.wait()
        try:
            if self._owned_transport is not None:
                self._owned_transport.close()
        finally:
            with self._condition:
                self._state = "CLOSED"
                self._condition.notify_all()

    def __enter__(self) -> Runa:
        with self._condition:
            if self._state != "OPEN":
                raise RuntimeError("Runa client is closed.")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> Literal[False]:
        del exc_type, exc, traceback
        self.close()
        return False


class AsyncWorkspaceSyncManager:
    """Asynchronous explicit bounded workspace synchronization operations."""

    __slots__ = ("_client",)

    def __init__(self, client: AsyncRuna, token: object = None) -> None:
        if token is not _ASYNC_WORKSPACE_SYNC_MANAGER_TOKEN:
            raise TypeError("AsyncWorkspaceSyncManager cannot be constructed directly.")
        self._client = client

    async def _mutation(
        self, operation: str, resource_id: str, request: object, key: str
    ) -> WorkspaceSyncEnvelope[object]:
        return cast(
            WorkspaceSyncEnvelope[object],
            await self._client._invoke(
                operation,
                path_values={"id": _validate_uuid(resource_id)},
                body=_workspace_sync_body(request),
                idempotency_key=_workspace_sync_key(key),
            ),
        )

    async def begin(
        self, workspace_id: str, request: WorkspaceSyncBeginRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncSession]:
        """Begin one bounded workspace synchronization session asynchronously."""

        if _validate_uuid(workspace_id) == request.workspace_binding_id:
            raise ConfigError() from None
        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncSession],
            await self._mutation("workspaces.sync.begin", workspace_id, request, idempotency_key),
        )

    async def negotiate(
        self, sync_id: str, request: WorkspaceSyncManifestPageRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]:
        """Negotiate one ordered manifest page asynchronously."""

        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt],
            await self._mutation("workspaces.sync.negotiate", sync_id, request, idempotency_key),
        )

    async def upload_chunk(
        self, sync_id: str, digest: str, data: bytes, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]:
        """Upload one content-addressed workspace chunk asynchronously."""

        if (
            re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(data, bytes)
            or len(data) > 8_388_608
        ):
            raise ConfigError() from None
        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt],
            await self._client._invoke(
                "workspaces.sync.chunk",
                path_values={"id": _validate_uuid(sync_id), "digest": digest},
                raw_body=bytes(data),
                idempotency_key=_workspace_sync_key(idempotency_key),
            ),
        )

    async def download_chunk(self, sync_id: str, digest: str) -> bytes:
        """Download one chunk as bytes after strict digest and length verification."""

        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ConfigError() from None
        envelope = cast(
            WorkspaceSyncEnvelope[WorkspaceSyncChunkContent],
            await self._client._invoke(
                "workspaces.sync.chunkDownload",
                path_values={"id": _validate_uuid(sync_id), "digest": digest},
            ),
        )
        if envelope.data.digest != digest or envelope.data.minimum_reader > 2:
            raise ApiError(200, code="malformed_response") from None
        return bytes(envelope.data.content)

    async def commit(
        self, sync_id: str, request: WorkspaceSyncCommitRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]:
        """Commit one complete synchronized workspace generation asynchronously."""

        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt],
            await self._mutation("workspaces.sync.commit", sync_id, request, idempotency_key),
        )

    async def changes(
        self, sync_id: str, options: WorkspaceSyncChangeOptions
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncChangePage]:
        """Read one ordered page of committed workspace changes asynchronously."""

        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncChangePage],
            await self._client._invoke(
                "workspaces.sync.changes",
                path_values={"id": _validate_uuid(sync_id)},
                query_values=_workspace_sync_query(options),
            ),
        )

    async def reconcile(
        self, workspace_id: str, request: WorkspaceSyncReconcileRequest, idempotency_key: str
    ) -> WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]:
        """Reconcile one workspace against an observed local generation asynchronously."""

        if _validate_uuid(workspace_id) == request.workspace_binding_id:
            raise ConfigError() from None
        return cast(
            WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt],
            await self._mutation(
                "workspaces.sync.reconcile", workspace_id, request, idempotency_key
            ),
        )


class AsyncWorkspaceBindingsManager:
    """Asynchronous canonical workspace binding operations."""

    __slots__ = ("_client",)

    def __init__(self, client: AsyncRuna, token: object = None) -> None:
        if token is not _ASYNC_WORKSPACE_BINDINGS_MANAGER_TOKEN:
            raise TypeError("AsyncWorkspaceBindingsManager cannot be constructed directly.")
        self._client = client

    async def create(
        self, request: WorkspaceBindingCreateRequest, idempotency_key: str
    ) -> WorkspaceBinding:
        """Create or exactly adopt one canonical workspace binding asynchronously."""

        value = cast(
            WorkspaceBinding,
            await self._client._invoke(
                "workspaceBindings.create",
                body=_binding_create_body(request),
                idempotency_key=_workspace_sync_key(idempotency_key),
            ),
        )
        return _require_binding_matches(value, request)

    async def get(self, binding_id: str, identity: WorkspaceBindingLookup) -> WorkspaceBinding:
        """Get one canonical binding using its complete identity asynchronously."""

        clean_binding_id = _validate_uuid(binding_id)
        if clean_binding_id == identity.workspace_id:
            raise ConfigError() from None
        value = cast(
            WorkspaceBinding,
            await self._client._invoke(
                "workspaceBindings.get",
                path_values={"binding_id": clean_binding_id},
                query_values=_binding_identity(identity),
            ),
        )
        return _require_binding_matches(value, identity, binding_id=clean_binding_id)


class AsyncMachineCreatesManager:
    """Asynchronous machine-create status and exact-name reconciliation."""

    __slots__ = ("_client",)

    def __init__(self, client: AsyncRuna, token: object = None) -> None:
        if token is not _ASYNC_MACHINE_CREATES_MANAGER_TOKEN:
            raise TypeError("AsyncMachineCreatesManager cannot be constructed directly.")
        self._client = client

    async def get(self, request_id: str) -> MachineCreateRequest:
        """Get one non-secret machine-create request state asynchronously."""

        return cast(
            MachineCreateRequest,
            await self._client._invoke(
                "machineCreates.get", path_values={"id": _validate_uuid(request_id)}
            ),
        )

    async def reconcile(self, request_id: str) -> MachineCreateRequest:
        """Reconcile one exact machine-create request state asynchronously."""

        return cast(
            MachineCreateRequest,
            await self._client._invoke(
                "machineCreates.reconcile", path_values={"id": _validate_uuid(request_id)}
            ),
        )


class AsyncSessionsManager:
    """Stable asynchronous session manager obtained from ``AsyncRuna.sessions``."""

    __slots__ = ("_client",)

    def __init__(self, client: AsyncRuna, token: object = None) -> None:
        if token is not _ASYNC_SESSIONS_MANAGER_TOKEN:
            raise TypeError("AsyncSessionsManager cannot be constructed directly.")
        self._client = client

    async def create(self, name: str, options: SessionCreateOptions) -> AsyncSession:
        """Create one session asynchronously.

        Args:
            name: Human-readable name of 1-80 characters.
            options: Explicit omission-aware creation options.
        Returns:
            A client-owned asynchronous session handle.
        Raises:
            ConfigError: If an input violates the local contract.
            ApiError: If the request fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSIONSMANAGER`` and ``TC-091-09``.
        """
        clean_name, clean_options = _validate_create(name, options)
        snapshot = cast(
            SessionSnapshot,
            await self._client._invoke(
                "sessions.create",
                body=_create_body(clean_name, clean_options),
                idempotency_key=_session_create_key(clean_options),
            ),
        )
        return AsyncSession(self, snapshot, _ASYNC_SESSION_TOKEN)

    async def list(self) -> list[AsyncSession]:
        """List visible sessions asynchronously.

        Returns:
            New client-owned asynchronous handles in service order.
        Raises:
            ApiError: If the request fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSIONSMANAGER`` and ``TC-091-09``.
        """
        snapshots = cast(list[SessionSnapshot], await self._client._invoke("sessions.list"))
        return [AsyncSession(self, item, _ASYNC_SESSION_TOKEN) for item in snapshots]

    async def get(self, session_id: str) -> AsyncSession:
        """Retrieve one session asynchronously.

        Args:
            session_id: Canonical lowercase session UUID.
        Returns:
            A client-owned handle whose ID matches ``session_id``.
        Raises:
            ConfigError: If ``session_id`` is not canonical.
            ApiError: If the request fails, is missing, or is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSIONSMANAGER`` and ``TC-091-09``.
        """
        clean_id = _validate_uuid(session_id)
        snapshot = cast(
            SessionSnapshot,
            await self._client._invoke("sessions.get", path_values={"id": clean_id}),
        )
        return AsyncSession(
            self, _require_matching_snapshot(snapshot, clean_id), _ASYNC_SESSION_TOKEN
        )

    async def _lifecycle(self, handle: AsyncSession, action: str) -> AsyncSession:
        snapshot = cast(
            SessionSnapshot,
            await self._client._invoke(f"sessions.{action}", path_values={"id": handle.id}),
        )
        handle._replace(_require_matching_snapshot(snapshot, handle.id))
        return handle

    async def _delete(self, handle: AsyncSession) -> Acknowledgement:
        return cast(
            Acknowledgement,
            await self._client._invoke("sessions.delete", path_values={"id": handle.id}),
        )

    async def _exec(
        self, handle: AsyncSession, command: str | Sequence[str], options: ExecOptions
    ) -> ExecResult:
        body, timeout_secs = _exec_body(command, options)
        return cast(
            ExecResult,
            await self._client._invoke(
                "sessions.exec",
                path_values={"id": handle.id},
                body=body,
                exec_timeout_secs=timeout_secs,
            ),
        )

    async def _checkpoint(self, handle: AsyncSession, name: str) -> Acknowledgement:
        if not isinstance(name, str) or not 1 <= len(name) <= 80:
            raise ConfigError() from None
        return cast(
            Acknowledgement,
            await self._client._invoke(
                "sessions.checkpoint",
                path_values={"id": handle.id},
                body=encode_for_operation("sessions.checkpoint", {"name": name}),
            ),
        )

    async def _open(self, handle: AsyncSession) -> OpenSessionResult:
        return cast(
            OpenSessionResult,
            await self._client._invoke("sessions.open", path_values={"id": handle.id}),
        )


class AsyncAgentSessionsManager:
    """Stable asynchronous manager for AgentSession process resources."""

    __slots__ = ("_client",)

    def __init__(self, client: AsyncRuna, token: object = None) -> None:
        if token is not _ASYNC_AGENT_SESSIONS_MANAGER_TOKEN:
            raise TypeError("AsyncAgentSessionsManager cannot be constructed directly.")
        self._client = client

    async def list(
        self,
        machine_id: str,
        options: AgentSessionListOptions | None = None,
    ) -> AgentSessionPage:
        """Return one bounded AgentSession page asynchronously."""

        clean_machine_id = _validate_uuid(machine_id)
        page = cast(
            AgentSessionPage,
            await self._client._invoke(
                "agentSessions.list",
                path_values={"id": clean_machine_id},
                query_values=_agent_session_query(options or AgentSessionListOptions()),
            ),
        )
        if any(item.machine_id != clean_machine_id for item in page.items):
            raise ApiError(200, code="malformed_response") from None
        return page

    async def create(self, machine_id: str, options: AgentSessionCreateOptions) -> AgentSession:
        """Create one durable AgentSession launch intent asynchronously."""

        clean_machine_id = _validate_uuid(machine_id)
        body, idempotency_key = _validate_agent_session_create(options)
        created = cast(
            AgentSession,
            await self._client._invoke(
                "agentSessions.create",
                path_values={"id": clean_machine_id},
                body=body,
                idempotency_key=idempotency_key,
            ),
        )
        if (
            created.machine_id != clean_machine_id
            or created.agent is not options.agent
            or created.cwd != options.cwd
            or created.workspace_binding_id != options.workspace_binding_id
            or created.workspace_generation != options.workspace_generation
        ):
            raise ApiError(201, code="malformed_response") from None
        return created

    async def get(self, agent_session_id: str) -> AgentSession:
        """Get one AgentSession asynchronously."""

        return await self._one("agentSessions.get", agent_session_id)

    async def agent_auth(self, agent_session: AgentSession) -> AgentSessionAuth:
        """Read fresh auth evidence bound to an already admitted AgentSession."""

        if not isinstance(agent_session, AgentSession):
            raise ConfigError() from None
        value = cast(
            AgentSessionAuth,
            await self._client._invoke(
                "agentSessions.agentAuth", path_values={"id": agent_session.id}
            ),
        )
        if (
            value.agent_session_id != agent_session.id
            or value.auth_mode is not agent_session.auth_mode
            or value.process_epoch != agent_session.process_epoch
        ):
            raise ApiError(200, code="malformed_response") from None
        return value

    async def rename(self, agent_session_id: str, name: str) -> AgentSession:
        """Rename AgentSession metadata asynchronously."""

        clean_name = _validate_agent_session_name(name)
        value = await self._one(
            "agentSessions.rename",
            agent_session_id,
            encode_for_operation("agentSessions.rename", {"name": clean_name}),
        )
        if value.name != clean_name:
            raise ApiError(200, code="malformed_response") from None
        return value

    async def terminate(self, agent_session_id: str) -> AgentSession:
        """Request durable termination asynchronously."""

        return await self._one("agentSessions.terminate", agent_session_id)

    async def create_terminal_connection(
        self,
        agent_session_id: str,
        options: TerminalConnectionCreateOptions,
    ) -> TerminalConnectionGrant:
        """Create terminal connection metadata without opening or consuming the stream."""

        clean_id = _validate_uuid(agent_session_id)
        body, idempotency_key = _validate_terminal_connection_create(options)
        return cast(
            TerminalConnectionGrant,
            await self._client._invoke(
                "agentSessions.createTerminalConnection",
                path_values={"id": clean_id},
                body=body,
                idempotency_key=idempotency_key,
            ),
        )

    async def _one(
        self,
        operation_key: str,
        agent_session_id: str,
        body: Mapping[str, object] | None = None,
    ) -> AgentSession:
        clean_id = _validate_uuid(agent_session_id)
        value = cast(
            AgentSession,
            await self._client._invoke(
                operation_key,
                path_values={"id": clean_id},
                body=body,
            ),
        )
        return _require_matching_agent_session(value, clean_id)


class AsyncCapabilitiesManager:
    """Stable asynchronous capability discovery manager.

    Examples:
        See ``REF-EX-ASYNCCAPABILITIESMANAGER`` and ``TC-091-09``.
    """

    __slots__ = ("_client",)

    def __init__(self, client: AsyncRuna, token: object = None) -> None:
        if token is not _ASYNC_CAPABILITIES_MANAGER_TOKEN:
            raise TypeError("AsyncCapabilitiesManager cannot be constructed directly.")
        self._client = client

    async def get(
        self,
        scope: CapabilityScope,
        resource_id: str | None = None,
    ) -> CapabilitySnapshot:
        """Get leased availability evidence without granting authority.

        Args:
            scope: Account, machine, or explicit AgentSession scope.
            resource_id: Required machine or AgentSession UUID; absent for account scope.
        Returns:
            A fresh account, machine, or AgentSession capability snapshot.
        Raises:
            ConfigError: If the scope and resource identifier do not form a valid request.
            ApiError: If discovery fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCCAPABILITIESMANAGER`` and ``TC-091-09``.
        """

        query = _capability_query(scope, resource_id)
        snapshot = cast(
            CapabilitySnapshot,
            await self._client._invoke("capabilities.get", query_values=query),
        )
        if snapshot.subject_scope is not scope or (
            scope is not CapabilityScope.ACCOUNT and snapshot.subject_id != resource_id
        ):
            raise ApiError(200, code="malformed_response") from None
        return snapshot


class AsyncRecordsManager:
    """Stable asynchronous records manager obtained from ``AsyncRuna.records``."""

    __slots__ = ("_client",)

    def __init__(self, client: AsyncRuna, token: object = None) -> None:
        if token is not _ASYNC_RECORDS_MANAGER_TOKEN:
            raise TypeError("AsyncRecordsManager cannot be constructed directly.")
        self._client = client

    async def list(self) -> list[Record]:
        """List visible records asynchronously.

        Returns:
            Immutable records in service order.
        Raises:
            ApiError: If the request fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCRECORDSMANAGER`` and ``TC-091-09``.
        """
        return cast(list[Record], await self._client._invoke("records.list"))


class AsyncSession:
    """Client-owned asynchronous session handle.

    Obtain instances from ``AsyncRuna.sessions``; direct construction raises ``TypeError``.
    """

    __slots__ = ("_manager", "_snapshot")

    def __init__(
        self,
        manager: AsyncSessionsManager,
        snapshot: SessionSnapshot,
        token: object = None,
    ) -> None:
        if token is not _ASYNC_SESSION_TOKEN:
            raise TypeError("AsyncSession cannot be constructed directly.")
        self._manager = manager
        self._snapshot = snapshot

    @property
    def id(self) -> str:
        """Return the canonical session UUID.

        Returns:
            The immutable identifier from the current snapshot.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return self._snapshot.id

    @property
    def snapshot(self) -> SessionSnapshot:
        """Return the latest immutable snapshot.

        Returns:
            The snapshot retained by this handle.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return self._snapshot

    def _replace(self, snapshot: SessionSnapshot) -> None:
        self._snapshot = snapshot

    async def refresh(self) -> AsyncSession:
        """Refresh this handle asynchronously.

        Returns:
            This same handle after replacing its snapshot.
        Raises:
            ApiError: If the request fails or the response ID is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        refreshed = await self._manager.get(self.id)
        if refreshed.id != self.id:
            raise ApiError(200, code="malformed_response")
        self._replace(refreshed.snapshot)
        return self

    async def start(self) -> AsyncSession:
        """Start this session asynchronously.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._lifecycle(self, "start")

    async def pause(self) -> AsyncSession:
        """Pause this session asynchronously.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._lifecycle(self, "pause")

    async def resume(self) -> AsyncSession:
        """Resume this session asynchronously.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._lifecycle(self, "resume")

    async def stop(self) -> AsyncSession:
        """Stop this session asynchronously.

        Returns:
            This handle with the returned snapshot.
        Raises:
            ApiError: If the lifecycle request fails or is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._lifecycle(self, "stop")

    async def delete(self) -> Acknowledgement:
        """Delete this session asynchronously.

        Returns:
            A successful acknowledgement.
        Raises:
            ApiError: If deletion fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._delete(self)

    async def exec(
        self,
        command: str | Sequence[str],
        options: ExecOptions = ExecOptions(),  # noqa: B008
    ) -> ExecResult:
        """Execute a command asynchronously.

        Args:
            command: Non-empty command string or non-empty argument sequence.
            options: Working directory and 1-600 second timeout options.
        Returns:
            Captured exit status, output, truncation flags, and duration.
        Raises:
            ConfigError: If the command or options violate the local contract.
            ApiError: If execution fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._exec(self, command, options)

    async def checkpoint(self, name: str) -> Acknowledgement:
        """Create a named checkpoint asynchronously.

        Args:
            name: Human-readable checkpoint name of 1-80 characters.
        Returns:
            A successful acknowledgement.
        Raises:
            ConfigError: If ``name`` violates the local contract.
            ApiError: If the request fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._checkpoint(self, name)

    async def open(self) -> OpenSessionResult:
        """Request a new session capability URL asynchronously.

        Returns:
            A sensitive result that must be assigned and never logged or displayed.
        Raises:
            ApiError: If the request fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCSESSION`` and ``TC-091-09``.
        """
        return await self._manager._open(self)


class AsyncRuna:
    """Asynchronous root client.

    Args:
        api_key: Explicit API key, otherwise resolved from accepted configuration.
        base_url: Optional explicit Cuna API origin. ``https://api.getcuna.com`` is canonical;
            ``https://api.runacode.io`` remains accepted for compatibility.
        config_file: Explicit configuration file path.
        diagnostic_sink: Optional disclosure-safe diagnostic sink.
        trace_sink: Optional disclosure-safe trace sink.
    Raises:
        ConfigError: If effective configuration is invalid.
    Examples:
        See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
    """

    __slots__ = (
        "_admitted",
        "_agent_sessions",
        "_capabilities",
        "_close_active",
        "_condition",
        "_config",
        "_diagnostic_sink",
        "_machine_creates",
        "_owned_transport",
        "_records",
        "_sessions",
        "_state",
        "_trace_sink",
        "_transport",
        "_workspace_bindings",
        "_workspace_sync",
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        config_file: str | os.PathLike[str] | None = None,
        diagnostic_sink: object | None = None,
        trace_sink: object | None = None,
    ) -> None:
        config = _config_or_raise(
            resolve_config(api_key=api_key, base_url=base_url, config_file=config_file)
        )
        self._initialize(config, None, diagnostic_sink, trace_sink)

    @classmethod
    def _with_transport(
        cls,
        *,
        transport: AsyncTransport,
        api_key: str | None = None,
        base_url: str | None = None,
        config_file: str | os.PathLike[str] | None = None,
        diagnostic_sink: object | None = None,
        trace_sink: object | None = None,
    ) -> AsyncRuna:
        instance = cls.__new__(cls)
        config = _config_or_raise(
            resolve_config(api_key=api_key, base_url=base_url, config_file=config_file)
        )
        instance._initialize(config, transport, diagnostic_sink, trace_sink)
        return instance

    def _initialize(
        self,
        config: EffectiveConfig,
        transport: AsyncTransport | None,
        diagnostic_sink: object | None,
        trace_sink: object | None,
    ) -> None:
        self._config = config
        self._condition = asyncio.Condition()
        self._state = "OPEN"
        self._close_active = False
        self._admitted = 0
        self._diagnostic_sink = diagnostic_sink
        self._trace_sink = trace_sink
        if transport is None:
            owned = AsyncHttpTransport(config.base_url)
            self._owned_transport: AsyncHttpTransport | None = owned
            self._transport: AsyncTransport = owned
        else:
            self._owned_transport = None
            self._transport = transport
        self._sessions = AsyncSessionsManager(self, _ASYNC_SESSIONS_MANAGER_TOKEN)
        self._agent_sessions = AsyncAgentSessionsManager(self, _ASYNC_AGENT_SESSIONS_MANAGER_TOKEN)
        self._capabilities = AsyncCapabilitiesManager(self, _ASYNC_CAPABILITIES_MANAGER_TOKEN)
        self._records = AsyncRecordsManager(self, _ASYNC_RECORDS_MANAGER_TOKEN)
        self._workspace_sync = AsyncWorkspaceSyncManager(self, _ASYNC_WORKSPACE_SYNC_MANAGER_TOKEN)
        self._workspace_bindings = AsyncWorkspaceBindingsManager(
            self, _ASYNC_WORKSPACE_BINDINGS_MANAGER_TOKEN
        )
        self._machine_creates = AsyncMachineCreatesManager(
            self, _ASYNC_MACHINE_CREATES_MANAGER_TOKEN
        )

    @property
    def sessions(self) -> AsyncSessionsManager:
        """Return the stable asynchronous sessions manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        return self._sessions

    @property
    def agent_sessions(self) -> AsyncAgentSessionsManager:
        """Return the stable asynchronous AgentSession manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """

        return self._agent_sessions

    @property
    def capabilities(self) -> AsyncCapabilitiesManager:
        """Return the stable asynchronous capability discovery manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """

        return self._capabilities

    @property
    def records(self) -> AsyncRecordsManager:
        """Return the stable asynchronous records manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        return self._records

    @property
    def workspace_sync(self) -> AsyncWorkspaceSyncManager:
        """Return the stable asynchronous workspace synchronization manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        return self._workspace_sync

    @property
    def workspace_bindings(self) -> AsyncWorkspaceBindingsManager:
        """Return asynchronous canonical workspace binding operations.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        return self._workspace_bindings

    @property
    def machine_creates(self) -> AsyncMachineCreatesManager:
        """Return asynchronous machine-create recovery operations.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        return self._machine_creates

    @asynccontextmanager
    async def _lease(self) -> AsyncIterator[None]:
        async with self._condition:
            if self._state != "OPEN":
                raise RuntimeError("Runa client is closed.")
            self._admitted += 1
        try:
            yield
        finally:
            async with self._condition:
                self._admitted -= 1
                self._condition.notify_all()

    async def _invoke(
        self,
        operation_key: str,
        *,
        path_values: Mapping[str, str] | None = None,
        query_values: Mapping[str, str] | None = None,
        body: Mapping[str, object] | None = None,
        raw_body: bytes | None = None,
        idempotency_key: str | None = None,
        exec_timeout_secs: int | None = None,
    ) -> object:
        async with self._lease():
            operation = OPERATIONS[operation_key]
            path = operation.path_template
            for key, value in (path_values or {}).items():
                path = path.replace(":" + key, value)
            if query_values:
                path += "?" + urlencode(query_values)
            prepared = prepare_request(
                operation_key=operation.key,
                method=operation.method,
                origin=self._config.base_url,
                relative_path=path,
                api_key=self._config.api_key,
                body=body,
                raw_body=raw_body,
                idempotency_key=idempotency_key,
                timeout_seconds=0,
            )
            observer: OperationObserver | NullObserver
            observer = (
                NullObserver()
                if self._diagnostic_sink is None and self._trace_sink is None
                else OperationObserver(operation, self._diagnostic_sink, self._trace_sink)
            )

            def cancellation_requested() -> bool:
                task = asyncio.current_task()
                cancelling = getattr(task, "cancelling", None)
                return callable(cancelling) and bool(cancelling())

            context = RequestContext(operation.key, observer.request_id, cancellation_requested)

            async def dispatch(timeout: float) -> object:
                if context.cancellation_requested():
                    raise asyncio.CancelledError
                attempt_request = PreparedRequest(
                    prepared.operation_key,
                    prepared.method,
                    prepared.origin,
                    prepared.relative_path,
                    prepared.headers,
                    prepared.body,
                    prepared.body_bytes,
                    timeout,
                )
                security_dispatch_guard(
                    attempt_request,
                    context,
                    expected_origin=self._config.base_url,
                    expected_operation_key=operation.key,
                    expected_method=operation.method,
                    expected_path=path,
                )
                raw = await self._transport(attempt_request, context)
                if context.cancellation_requested():
                    raise asyncio.CancelledError
                value = disposition(raw, operation.success_status)
                if context.cancellation_requested():
                    raise asyncio.CancelledError
                try:
                    decoded = decode_for_operation(operation_key, value)
                    if operation_key == "capabilities.get":
                        return _validate_capability_response(decoded, raw.headers)
                    if operation_key == "agentSessions.agentAuth":
                        return _validate_agent_auth_headers(decoded, raw.headers)
                    return decoded
                except DecodeFailure:
                    raise ApiError(raw.status, code="malformed_response") from None

            try:
                result = await run_async(
                    operation_key,
                    dispatch,
                    observer,
                    timeout_secs=exec_timeout_secs,
                )
                observer.end("success")
                return result
            except asyncio.CancelledError as error:
                observer.end("cancelled")
                raise error
            except BaseException as error:
                observer.end("error", error)
                raise

    async def me(self) -> Me:
        """Read the authenticated account asynchronously.

        Returns:
            Account identity and workspace assignment.
        Raises:
            ApiError: If the request fails or the response is malformed.
            asyncio.CancelledError: If the caller cancels the operation.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        return cast(Me, await self._invoke("me.get"))

    async def close(self) -> None:
        """Close client-owned resources asynchronously.

        Returns:
            ``None`` after all admitted operations and owned transport close.
        Raises:
            asyncio.CancelledError: If cancellation interrupts an active close leader.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        leader = False
        async with self._condition:
            if self._state == "OPEN":
                self._state = "CLOSING"
                self._close_active = True
                leader = True
            elif self._state == "CLOSING" and not self._close_active:
                self._close_active = True
                leader = True
            while not leader and self._state != "CLOSED":
                await self._condition.wait()
                if self._state == "CLOSING" and not self._close_active:
                    self._close_active = True
                    leader = True
            if self._state == "CLOSED":
                return
            while self._admitted:
                await self._condition.wait()
        try:
            if self._owned_transport is not None:
                await self._owned_transport.close()
        except asyncio.CancelledError:
            async with self._condition:
                self._close_active = False
                self._condition.notify_all()
            raise
        else:
            async with self._condition:
                self._state = "CLOSED"
                self._close_active = False
                self._condition.notify_all()

    async def __aenter__(self) -> AsyncRuna:
        async with self._condition:
            if self._state != "OPEN":
                raise RuntimeError("Runa client is closed.")
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> Literal[False]:
        del exc_type, exc, traceback
        await self.close()
        return False


__all__ = (
    "AsyncCapabilitiesManager",
    "AsyncMachineCreatesManager",
    "AsyncRecordsManager",
    "AsyncRuna",
    "AsyncSession",
    "AsyncSessionsManager",
    "AsyncWorkspaceBindingsManager",
    "AsyncWorkspaceSyncManager",
    "CapabilitiesManager",
    "MachineCreatesManager",
    "RecordsManager",
    "Runa",
    "Session",
    "SessionsManager",
    "WorkspaceBindingsManager",
    "WorkspaceSyncManager",
)

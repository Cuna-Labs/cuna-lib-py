"""Public synchronous and asynchronous Runa clients."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from contextlib import asynccontextmanager, contextmanager
from typing import Literal, TypeVar, cast

from runa.errors import ApiError, ConfigError
from runa.models import (
    UNSET,
    Acknowledgement,
    ExecOptions,
    ExecResult,
    Me,
    OpenSessionResult,
    Record,
    SessionAgent,
    SessionCreateOptions,
    SessionSnapshot,
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
)

_T = TypeVar("_T")


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


def _validate_create(name: object, options: object) -> tuple[str, SessionCreateOptions]:
    if not isinstance(name, str) or not 1 <= len(name) <= 80:
        raise ConfigError() from None
    if not isinstance(options, SessionCreateOptions):
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
    return name, options


def _create_body(name: str, options: SessionCreateOptions) -> dict[str, object]:
    supplied: dict[str, object] = {"name": name}
    for key in ("agent", "vcpus", "memory_mib", "allowed_hosts", "runtime_port"):
        value = getattr(options, key)
        if value is not UNSET:
            if key == "agent" and hasattr(value, "value"):
                supplied[key] = value.value
            elif key == "allowed_hosts":
                supplied[key] = list(value)
            else:
                supplied[key] = value
    return encode_for_operation("sessions.create", supplied)


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
_RECORDS_MANAGER_TOKEN = object()
_SESSION_TOKEN = object()
_ASYNC_SESSIONS_MANAGER_TOKEN = object()
_ASYNC_RECORDS_MANAGER_TOKEN = object()
_ASYNC_SESSION_TOKEN = object()


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
            self._client._invoke("sessions.create", body=_create_body(clean_name, clean_options)),
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
        base_url: HTTPS service origin override.
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
        "_condition",
        "_config",
        "_diagnostic_sink",
        "_owned_transport",
        "_records",
        "_sessions",
        "_state",
        "_trace_sink",
        "_transport",
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
        self._records = RecordsManager(self, _RECORDS_MANAGER_TOKEN)

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
    def records(self) -> RecordsManager:
        """Return the stable records manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-RUNA`` and ``TC-091-09``.
        """
        return self._records

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
        body: Mapping[str, object] | None = None,
        exec_timeout_secs: int | None = None,
    ) -> object:
        with self._lease():
            operation = OPERATIONS[operation_key]
            path = operation.path_template
            for key, value in (path_values or {}).items():
                path = path.replace("{" + key + "}", value)
            prepared = prepare_request(
                operation_key=operation.key,
                method=operation.method,
                origin=self._config.base_url,
                relative_path=path,
                api_key=self._config.api_key,
                body=body,
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
                raw = self._transport(
                    PreparedRequest(
                        prepared.operation_key,
                        prepared.method,
                        prepared.origin,
                        prepared.relative_path,
                        prepared.headers,
                        prepared.body,
                        prepared.body_bytes,
                        timeout,
                    ),
                    context,
                )
                value = disposition(raw, operation.success_status)
                try:
                    return decode_for_operation(operation_key, value)
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
                "sessions.create", body=_create_body(clean_name, clean_options)
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
        base_url: HTTPS service origin override.
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
        "_close_active",
        "_condition",
        "_config",
        "_diagnostic_sink",
        "_owned_transport",
        "_records",
        "_sessions",
        "_state",
        "_trace_sink",
        "_transport",
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
        self._records = AsyncRecordsManager(self, _ASYNC_RECORDS_MANAGER_TOKEN)

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
    def records(self) -> AsyncRecordsManager:
        """Return the stable asynchronous records manager.

        Returns:
            The manager owned by this client.
        Examples:
            See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.
        """
        return self._records

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
        body: Mapping[str, object] | None = None,
        exec_timeout_secs: int | None = None,
    ) -> object:
        async with self._lease():
            operation = OPERATIONS[operation_key]
            path = operation.path_template
            for key, value in (path_values or {}).items():
                path = path.replace("{" + key + "}", value)
            prepared = prepare_request(
                operation_key=operation.key,
                method=operation.method,
                origin=self._config.base_url,
                relative_path=path,
                api_key=self._config.api_key,
                body=body,
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
                raw = await self._transport(
                    PreparedRequest(
                        prepared.operation_key,
                        prepared.method,
                        prepared.origin,
                        prepared.relative_path,
                        prepared.headers,
                        prepared.body,
                        prepared.body_bytes,
                        timeout,
                    ),
                    context,
                )
                if context.cancellation_requested():
                    raise asyncio.CancelledError
                value = disposition(raw, operation.success_status)
                if context.cancellation_requested():
                    raise asyncio.CancelledError
                try:
                    return decode_for_operation(operation_key, value)
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
    "AsyncRecordsManager",
    "AsyncRuna",
    "AsyncSession",
    "AsyncSessionsManager",
    "RecordsManager",
    "Runa",
    "Session",
    "SessionsManager",
)

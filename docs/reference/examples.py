"""Canonical safe, public-surface-only API reference examples.

The examples are compiled by the documentation gate and can be invoked with
synthetic public-shaped fixtures without credentials, DNS, or network access.
"""

from __future__ import annotations

from runa import (
    UNSET,
    Acknowledgement,
    AssignedWorkspace,
    AsyncRecordsManager,
    AsyncRuna,
    AsyncSession,
    AsyncSessionsManager,
    EstimatedUsage,
    ExecOptions,
    ExecResult,
    Me,
    OpenSessionResult,
    Record,
    RecordsManager,
    Runa,
    Session,
    SessionAgent,
    SessionCreateOptions,
    SessionsManager,
    SessionSnapshot,
    SessionStatus,
    UnassignedWorkspace,
    UnsetType,
)
from runa.errors import ApiError, CommandError, ConfigError, RunaError


def runa(client: Runa) -> None:
    account = client.me()
    sessions = client.sessions
    records = client.records
    del account, sessions, records


def sessions_manager(manager: SessionsManager, options: SessionCreateOptions) -> None:
    created = manager.create("reference", options)
    listed = manager.list()
    loaded = manager.get(created.id)
    del listed, loaded


def records_manager(manager: RecordsManager) -> None:
    records = manager.list()
    del records


def session(handle: Session) -> None:
    refreshed = handle.refresh()
    result = handle.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    opened = handle.open()
    del refreshed, result, opened


async def async_runa(client: AsyncRuna) -> None:
    account = await client.me()
    sessions = client.sessions
    records = client.records
    del account, sessions, records


async def async_sessions_manager(
    manager: AsyncSessionsManager, options: SessionCreateOptions
) -> None:
    created = await manager.create("reference", options)
    listed = await manager.list()
    loaded = await manager.get(created.id)
    del listed, loaded


async def async_records_manager(manager: AsyncRecordsManager) -> None:
    records = await manager.list()
    del records


async def async_session(handle: AsyncSession) -> None:
    refreshed = await handle.refresh()
    result = await handle.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    opened = await handle.open()
    del refreshed, result, opened


def acknowledgement(value: Acknowledgement) -> bool:
    return value.ok


def assigned_workspace(value: AssignedWorkspace) -> EstimatedUsage:
    return value.usage


def estimated_usage(value: EstimatedUsage) -> float:
    return float(value.estimated_remaining_usd)


def exec_options() -> ExecOptions:
    return ExecOptions(cwd="/workspace", timeout_secs=30)


def exec_result(value: ExecResult) -> int:
    return value.exit_code


def me(value: Me) -> str:
    return value.email


def open_session_result(value: OpenSessionResult) -> None:
    result = value
    del result


def record(value: Record) -> str:
    return value.summary


def session_agent() -> SessionAgent:
    return SessionAgent.CODEX


def session_create_options() -> SessionCreateOptions:
    return SessionCreateOptions(agent=SessionAgent.CODEX, memory_mib=2048)


def session_snapshot(value: SessionSnapshot) -> SessionStatus:
    return value.status


def session_status() -> SessionStatus:
    return SessionStatus.RUNNING


def unset() -> object:
    return UNSET


def unassigned_workspace(value: UnassignedWorkspace) -> int:
    return value.waitlist_position


def unset_type(value: UnsetType) -> str:
    return repr(value)


def api_error(error: ApiError) -> int:
    return error.status


def command_error(error: CommandError) -> str:
    return error.code


def config_error(error: ConfigError) -> str:
    return error.message


def runa_error(error: RunaError) -> str:
    return error.code

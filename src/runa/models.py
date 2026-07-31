"""Immutable public Runa domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class SessionStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    STOPPED = "stopped"
    DELETED = "deleted"
    ERROR = "error"


class SessionAgent(str, Enum):
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    OPENCLAW = "openclaw"


_UNSET_TOKEN = object()


class UnsetType:
    """Type of the sole public omission marker, :data:`UNSET`."""

    __slots__ = ()

    def __new__(cls, token: object = None) -> UnsetType:
        if token is not _UNSET_TOKEN:
            raise TypeError("UnsetType cannot be constructed; use UNSET.")
        return super().__new__(cls)

    def __repr__(self) -> str:
        return "UNSET"

    def __reduce__(self) -> str:
        return "UNSET"


UNSET = UnsetType(_UNSET_TOKEN)


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    id: str
    user_id: object
    slug: object
    name: object
    agent: SessionAgent | None
    vcpus: object
    memory_mib: object
    status: SessionStatus
    running_seconds: object
    created_at: object
    updated_at: object
    url: str


@dataclass(frozen=True, slots=True)
class SessionCreateOptions:
    agent: SessionAgent | UnsetType = UNSET
    vcpus: object | UnsetType = UNSET
    memory_mib: object | UnsetType = UNSET
    allowed_hosts: object | UnsetType = UNSET
    runtime_port: object | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class ExecOptions:
    cwd: str | UnsetType = UNSET
    timeout_secs: int | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class ExecResult:
    exit_code: object
    stdout: object
    stderr: object
    duration_ms: object
    stdout_truncated: object
    stderr_truncated: object


@dataclass(frozen=True, slots=True)
class Acknowledgement:
    ok: Literal[True]


@dataclass(frozen=True, slots=True)
class OpenSessionResult:
    url: str


@dataclass(frozen=True, slots=True)
class Record:
    id: object
    session_id: object
    kind: object
    summary: object
    detail: object
    created_at: object


@dataclass(frozen=True, slots=True)
class EstimatedUsage:
    estimated_spend_usd: object
    estimated_remaining_usd: object
    note: object


@dataclass(frozen=True, slots=True)
class AssignedWorkspace:
    assigned: bool
    usage: EstimatedUsage


@dataclass(frozen=True, slots=True)
class UnassignedWorkspace:
    assigned: Literal[False]
    waitlist_position: object


@dataclass(frozen=True, slots=True)
class Me:
    id: object
    email: object
    workspace: AssignedWorkspace | UnassignedWorkspace

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
    user_id: str
    slug: str
    name: str
    agent: SessionAgent | None
    vcpus: int
    memory_mib: int
    status: SessionStatus
    running_seconds: int
    created_at: str
    updated_at: str
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
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    stdout_truncated: bool
    stderr_truncated: bool


@dataclass(frozen=True, slots=True)
class Acknowledgement:
    ok: Literal[True]


@dataclass(frozen=True, slots=True)
class OpenSessionResult:
    url: str


@dataclass(frozen=True, slots=True)
class Record:
    id: str
    session_id: str
    kind: str
    summary: str
    detail: object
    created_at: str


@dataclass(frozen=True, slots=True)
class EstimatedUsage:
    estimated_spend_usd: int | float
    estimated_remaining_usd: int | float
    note: str


@dataclass(frozen=True, slots=True)
class AssignedWorkspace:
    assigned: Literal[True]
    usage: EstimatedUsage


@dataclass(frozen=True, slots=True)
class UnassignedWorkspace:
    assigned: Literal[False]
    waitlist_position: int


@dataclass(frozen=True, slots=True)
class Me:
    id: str
    email: str
    workspace: AssignedWorkspace | UnassignedWorkspace

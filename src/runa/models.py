"""Immutable public Runa domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class SessionStatus(str, Enum):
    """Session lifecycle state.

    Attributes:
        CREATING: Provisioning is in progress.
        RUNNING: The session is running.
        PAUSED: The session is paused.
        SUSPENDED: The service suspended the session.
        STOPPED: The session is stopped.
        DELETED: The session was deleted.
        ERROR: The session entered an error state.
    Examples:
        See ``REF-EX-SESSIONSTATUS`` and ``TC-091-09``.
    """

    CREATING = "creating"
    RUNNING = "running"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    STOPPED = "stopped"
    DELETED = "deleted"
    ERROR = "error"


class SessionAgent(str, Enum):
    """Supported session agent.

    Attributes:
        CLAUDE_CODE: Claude Code agent.
        CODEX: Codex agent.
        OPENCLAW: OpenClaw agent.
    Examples:
        See ``REF-EX-SESSIONAGENT`` and ``TC-091-09``.
    """

    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    OPENCLAW = "openclaw"


class OutboundPolicyMode(str, Enum):
    """Public outbound network policy mode."""

    ALLOWLIST = "allowlist"
    DENYLIST = "denylist"


_UNSET_TOKEN = object()


class UnsetType:
    """Type of the sole public omission marker, ``UNSET``.

    Raises:
        TypeError: On every direct construction attempt.
    Examples:
        See ``REF-EX-UNSETTYPE`` and ``TC-091-09``.
    """

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
"""Sole public omission marker.

Examples:
    See ``REF-EX-UNSET`` and ``TC-091-09``.
"""


@dataclass(frozen=True, slots=True)
class OutboundPolicy:
    """Allow-list or deny-list policy for a newly created session.

    An empty ``hosts`` list is explicit and retains the selected mode's semantics.
    """

    mode: OutboundPolicyMode
    hosts: list[str]


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    """Immutable session state.

    Attributes:
        id: Canonical session UUID.
        user_id: Canonical owner identifier.
        slug: Stable service slug.
        name: Human-readable session name.
        agent: Selected agent or ``None``.
        vcpus: Allocated virtual CPUs.
        memory_mib: Allocated memory in MiB.
        status: Current lifecycle state.
        running_seconds: Accumulated running time.
        created_at: RFC 3339 creation timestamp.
        updated_at: RFC 3339 update timestamp.
        url: Sensitive capability URL; never log, display, persist, or reuse.
    Examples:
        See ``REF-EX-SESSIONSNAPSHOT`` and ``TC-091-09``.
    """

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
    """Omission-aware session creation options.

    Attributes:
        agent: Agent or ``UNSET``.
        vcpus: Integer from 1 through 8 or ``UNSET``.
        memory_mib: Integer from 512 through 16384 or ``UNSET``.
        allowed_hosts: Legacy allow list or ``UNSET``.
        outbound_policy: Explicit allow-list or deny-list policy or ``UNSET``.
        runtime_port: Integer from 1 through 65535 or ``UNSET``.
    Examples:
        See ``REF-EX-SESSIONCREATEOPTIONS`` and ``TC-091-09``.
    """

    agent: SessionAgent | UnsetType = UNSET
    vcpus: int | UnsetType = UNSET
    memory_mib: int | UnsetType = UNSET
    allowed_hosts: list[str] | UnsetType = UNSET
    outbound_policy: OutboundPolicy | UnsetType = UNSET
    runtime_port: int | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class ExecOptions:
    """Omission-aware command execution options.

    Attributes:
        cwd: Working directory or ``UNSET``.
        timeout_secs: Integer from 1 through 600 or ``UNSET``.
    Examples:
        See ``REF-EX-EXECOPTIONS`` and ``TC-091-09``.
    """

    cwd: str | UnsetType = UNSET
    timeout_secs: int | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class ExecResult:
    """Immutable command result.

    Attributes:
        exit_code: Process exit code.
        stdout: Captured standard output.
        stderr: Captured standard error.
        duration_ms: Command duration in milliseconds.
        stdout_truncated: Whether standard output was truncated.
        stderr_truncated: Whether standard error was truncated.
    Examples:
        See ``REF-EX-EXECRESULT`` and ``TC-091-09``.
    """

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    stdout_truncated: bool
    stderr_truncated: bool


@dataclass(frozen=True, slots=True)
class Acknowledgement:
    """Immutable successful acknowledgement.

    Attributes:
        ok: Literal ``True``.
    Examples:
        See ``REF-EX-ACKNOWLEDGEMENT`` and ``TC-091-09``.
    """

    ok: Literal[True]


@dataclass(frozen=True, slots=True)
class OpenSessionResult:
    """Sensitive open-session result.

    Attributes:
        url: Capability URL; assign it and never log, display, persist, or reuse it.
    Examples:
        See ``REF-EX-OPENSESSIONRESULT`` and ``TC-091-09``.
    """

    url: str


@dataclass(frozen=True, slots=True)
class Record:
    """Immutable workspace record.

    Attributes:
        id: Canonical record identifier.
        session_id: Canonical parent session UUID.
        kind: Record kind discriminator.
        summary: Disclosure-safe summary.
        detail: Contract-defined detail retained without hidden filtering.
        created_at: RFC 3339 creation timestamp.
    Examples:
        See ``REF-EX-RECORD`` and ``TC-091-09``.
    """

    id: str
    session_id: str
    kind: str
    summary: str
    detail: object
    created_at: str


@dataclass(frozen=True, slots=True)
class EstimatedUsage:
    """Estimated workspace usage.

    Attributes:
        estimated_spend_usd: Estimated USD spend.
        estimated_remaining_usd: Estimated remaining USD balance.
        note: Service-provided usage note.
    Examples:
        See ``REF-EX-ESTIMATEDUSAGE`` and ``TC-091-09``.
    """

    estimated_spend_usd: int | float
    estimated_remaining_usd: int | float
    note: str


@dataclass(frozen=True, slots=True)
class AssignedWorkspace:
    """Assigned workspace state.

    Attributes:
        assigned: Literal ``True`` discriminator.
        usage: Estimated workspace usage.
    Examples:
        See ``REF-EX-ASSIGNEDWORKSPACE`` and ``TC-091-09``.
    """

    assigned: Literal[True]
    usage: EstimatedUsage


@dataclass(frozen=True, slots=True)
class UnassignedWorkspace:
    """Unassigned workspace state.

    Attributes:
        assigned: Literal ``False`` discriminator.
        waitlist_position: Current one-based waitlist position.
    Examples:
        See ``REF-EX-UNASSIGNEDWORKSPACE`` and ``TC-091-09``.
    """

    assigned: Literal[False]
    waitlist_position: int


@dataclass(frozen=True, slots=True)
class Me:
    """Authenticated account state.

    Attributes:
        id: Canonical account identifier.
        email: Authenticated email address.
        workspace: Assigned or unassigned workspace state.
    Examples:
        See ``REF-EX-ME`` and ``TC-091-09``.
    """

    id: str
    email: str
    workspace: AssignedWorkspace | UnassignedWorkspace

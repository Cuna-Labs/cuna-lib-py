"""Immutable public Runa domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, Literal, TypeVar


class CapabilityScope(str, Enum):
    """Scope accepted by capability discovery.

    Attributes:
        ACCOUNT: Account-wide capability evidence.
        MACHINE: Evidence for one machine UUID.
        AGENT_SESSION: Evidence for one AgentSession UUID.
    Examples:
        See ``REF-EX-CAPABILITYSCOPE`` and ``TC-091-09``.
    """

    ACCOUNT = "account"
    MACHINE = "machine"
    AGENT_SESSION = "agent_session"


class CapabilityAvailability(str, Enum):
    """Current availability reported for a capability.

    Attributes:
        SUPPORTED: The capability is currently supported.
        UNSUPPORTED: The capability is not implemented.
        TEMPORARILY_UNAVAILABLE: The capability is known but not currently usable.
        UNKNOWN: Availability cannot be established safely.
    Examples:
        See ``REF-EX-CAPABILITYAVAILABILITY`` and ``TC-091-09``.
    """

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    UNKNOWN = "unknown"


class CapabilitySurface(str, Enum):
    """Product surface on which a capability can be used.

    Attributes:
        CLI: Command-line interface.
        WEB: Authenticated web console.
        SDK: Public software development kit.
    Examples:
        See ``REF-EX-CAPABILITYSURFACE`` and ``TC-091-09``.
    """

    CLI = "cli"
    WEB = "web"
    SDK = "sdk"


class CapabilityInteraction(str, Enum):
    """Interaction required to use a capability.

    Attributes:
        NATIVE: Native operation on the selected surface.
        READ_ONLY: Observation without mutation.
        BROWSER_HANDOFF: Browser-mediated handoff.
    Examples:
        See ``REF-EX-CAPABILITYINTERACTION`` and ``TC-091-09``.
    """

    NATIVE = "native"
    READ_ONLY = "read_only"
    BROWSER_HANDOFF = "browser_handoff"


class CapabilityMutationClass(str, Enum):
    """Consequence class of the operation behind a capability.

    Attributes:
        NONE: No mutation.
        REVERSIBLE: Reversible mutation.
        DESTRUCTIVE: Destructive mutation.
        SECRET_REVEALING: Operation may reveal a secret.
        FINANCIAL: Operation may create financial consequences.
    Examples:
        See ``REF-EX-CAPABILITYMUTATIONCLASS`` and ``TC-091-09``.
    """

    NONE = "none"
    REVERSIBLE = "reversible"
    DESTRUCTIVE = "destructive"
    SECRET_REVEALING = "secret_revealing"  # noqa: S105 - public contract vocabulary
    FINANCIAL = "financial"


@dataclass(frozen=True, slots=True)
class Capability:
    """Immutable capability description returned by discovery.

    Attributes:
        id: Stable capability identifier.
        availability: Current availability.
        surfaces: Supported product surfaces.
        interaction: Required interaction mode.
        mutation_class: Consequence class.
        required_permissions: Permissions required by the protected operation.
        reason_code: Optional safe explanation for non-availability.
    Examples:
        See ``REF-EX-CAPABILITY`` and ``TC-091-09``.
    """

    id: str
    availability: CapabilityAvailability
    surfaces: tuple[CapabilitySurface, ...]
    interaction: CapabilityInteraction
    mutation_class: CapabilityMutationClass
    required_permissions: tuple[str, ...]
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilitySnapshot:
    """Leased capability evidence for one account, machine, or AgentSession.

    Attributes:
        schema_version: Capability schema version.
        subject_scope: Account, machine, or AgentSession scope represented by the snapshot.
        subject_id: Machine or AgentSession UUID for resource-scoped evidence.
        observed_at: RFC 3339 observation timestamp.
        expires_at: RFC 3339 evidence expiry timestamp.
        etag: Unquoted semantic evidence digest.
        capabilities: Ordered capability descriptions.
    Examples:
        See ``REF-EX-CAPABILITYSNAPSHOT`` and ``TC-091-09``.
    """

    schema_version: Literal["1.0"]
    subject_scope: Literal[
        CapabilityScope.ACCOUNT,
        CapabilityScope.MACHINE,
        CapabilityScope.AGENT_SESSION,
    ]
    subject_id: str | None
    observed_at: str
    expires_at: str
    etag: str
    capabilities: tuple[Capability, ...]


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


class AgentSessionAuthMode(str, Enum):
    """Authentication binding selected for an AgentSession process."""

    INTERACTIVE_LOGIN = "interactive_login"
    CREDENTIAL_BINDING = "credential_binding"


class AgentSessionAuthState(str, Enum):
    """Closed authentication evidence state for one AgentSession generation.

    Attributes:
        LOGIN_REQUIRED: Interactive login has not completed.
        AUTHENTICATED: Provider CLI evidence confirms interactive authentication.
        CONFIGURED: Credential authority confirms the admitted binding is configured.
        UNAVAILABLE: The adapter cannot produce authoritative positive evidence.
    """

    LOGIN_REQUIRED = "login_required"
    AUTHENTICATED = "authenticated"
    CONFIGURED = "configured"
    UNAVAILABLE = "unavailable"


class AgentSessionAuthEvidenceClass(str, Enum):
    """Authority class that produced an AgentSession authentication observation.

    Attributes:
        PROVIDER_CLI_LOGIN_STATUS: Evidence read from the provider CLI authority.
        CREDENTIAL_BINDING_AUTHORITY: Evidence read from Cuna's binding authority.
        INSUFFICIENT: Negative evidence because no positive authority was available.
    """

    PROVIDER_CLI_LOGIN_STATUS = "provider_cli_login_status"
    CREDENTIAL_BINDING_AUTHORITY = "credential_binding_authority"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class AgentSessionAuth:
    """Immutable short-lived evidence for one exact AgentSession process generation.

    Attributes:
        observation_id: Canonical UUID of this observation.
        agent_session_id: Exact AgentSession UUID to which the evidence belongs.
        process_epoch: Exact process generation UUID, or no epoch for negative evidence.
        auth_mode: Authentication mode admitted for the AgentSession.
        agent_version: Observed provider-agent semantic version.
        adapter_version: Closed Cuna authentication-adapter contract version.
        evidence_class: Authority class that produced the observation.
        observed_at: RFC 3339 observation timestamp.
        valid_until: RFC 3339 expiry no more than 30 seconds after observation.
        state: Closed secret-free authentication evidence state.
    """

    observation_id: str
    agent_session_id: str
    process_epoch: str | None
    auth_mode: AgentSessionAuthMode
    agent_version: str
    adapter_version: Literal["runa.agent-auth.v1"]
    evidence_class: AgentSessionAuthEvidenceClass
    observed_at: str
    valid_until: str
    state: AgentSessionAuthState


class AgentSessionDesiredState(str, Enum):
    """Durable desired state for an AgentSession."""

    RUNNING = "running"
    TERMINATED = "terminated"


class AgentSessionRequestState(str, Enum):
    """Durable request processing state for an AgentSession."""

    LAUNCH_PENDING = "launch_pending"
    RUNTIME_CLAIMED = "runtime_claimed"
    LAUNCHED = "launched"
    TERMINATION_PENDING = "termination_pending"
    TERMINAL = "terminal"
    FAILED = "failed"


class AgentSessionProcessState(str, Enum):
    """Observed process fact; ``UNKNOWN`` is not proof of absence."""

    UNKNOWN = "unknown"
    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    EXITED = "exited"
    FAILED = "failed"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


@dataclass(frozen=True, slots=True)
class AgentSession:
    """Immutable AgentSession intent and observed process facts."""

    id: str
    machine_id: str
    name: str
    agent: SessionAgent
    cwd: str
    auth_mode: AgentSessionAuthMode
    desired_state: AgentSessionDesiredState
    request_state: AgentSessionRequestState
    process_state: AgentSessionProcessState
    row_version: int
    created_at: str
    updated_at: str
    workspace_binding_id: str | None = None
    workspace_generation: int | None = None
    process_epoch: str | None = None
    runtime_observed_at: str | None = None
    runtime_expires_at: str | None = None
    termination_requested_at: str | None = None


@dataclass(frozen=True, slots=True)
class AgentSessionPage:
    """One bounded AgentSession page with an opaque continuation cursor."""

    items: tuple[AgentSession, ...]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class AgentSessionListOptions:
    """Optional bounded pagination controls for AgentSession listing."""

    limit: int | None = None
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class AgentSessionCreateOptions:
    """AgentSession creation request and caller-stable idempotency identity."""

    idempotency_key: str
    agent: SessionAgent
    cwd: str
    workspace_binding_id: str
    workspace_generation: int
    name: str | None = None
    auth_mode: AgentSessionAuthMode | None = None
    credential_binding_id: str | None = None


class TerminalConnectionCapabilityName(str, Enum):
    """Capability names negotiated for the terminal stream protocol."""

    ACKNOWLEDGEMENT = "acknowledgement"
    HEARTBEAT = "heartbeat"
    LIVE_RESIZE = "live_resize"
    RESUME = "resume"
    SIGNALS = "signals"


class TerminalConnectionAvailability(str, Enum):
    """Availability of one terminal stream capability."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TerminalConnectionCapability:
    """One closed terminal stream capability record."""

    name: TerminalConnectionCapabilityName
    availability: TerminalConnectionAvailability


@dataclass(frozen=True, slots=True)
class TerminalConnectionCreateOptions:
    """Caller-stable options for creating one terminal connection grant."""

    idempotency_key: str
    client_instance_id: str
    resume_handle: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalConnectionGrant:
    """Short-lived metadata grant; the SDK does not consume or open its stream."""

    terminal_session_id: str
    resume_handle: str
    connect_url: str
    connect_token: str = field(repr=False)
    protocol: Literal["runa.terminal.v1"]
    capabilities: tuple[TerminalConnectionCapability, ...]
    expires_at: str


class OutboundPolicyMode(str, Enum):
    """Public outbound network policy mode.

    Attributes:
        ALLOWLIST: Permit only listed work destinations.
        DENYLIST: Block listed work destinations and permit the others.
    Examples:
        See ``REF-EX-OUTBOUNDPOLICYMODE`` and ``TC-091-09``.
    """

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

    Attributes:
        mode: Selected allow-list or deny-list behavior.
        hosts: Exact-domain or leading-wildcard host rules.
    Examples:
        See ``REF-EX-OUTBOUNDPOLICY`` and ``TC-091-09``.
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

    idempotency_key: str | None = None
    agent: SessionAgent | UnsetType = UNSET
    vcpus: int | UnsetType = UNSET
    memory_mib: int | UnsetType = UNSET
    allowed_hosts: list[str] | UnsetType = UNSET
    outbound_policy: OutboundPolicy | UnsetType = UNSET
    runtime_port: int | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class WorkspaceSyncProtocolRange:
    """Inclusive workspace synchronization protocol range."""

    minimum: int
    maximum: int


@dataclass(frozen=True, slots=True)
class WorkspaceSyncBeginRequest:
    """Authority-bound request to begin workspace synchronization."""

    workspace_binding_id: str
    machine_id: str
    base_generation: int
    exclusion_policy_digest: str
    protocol: WorkspaceSyncProtocolRange
    minimum_reader: int
    minimum_writer: int


@dataclass(frozen=True, slots=True)
class WorkspaceSyncManifestPageRequest:
    """One bounded ordered workspace manifest page."""

    page_index: int
    is_last: bool
    minimum_reader: int
    minimum_writer: int
    entries: list[WorkspaceSyncManifestEntry]


@dataclass(frozen=True, slots=True)
class WorkspaceSyncCommitRequest:
    """Request to atomically commit a synchronized workspace generation."""

    expected_generation: int
    exclusion_policy_digest: str
    manifest_root: str
    minimum_reader: int
    minimum_writer: int


@dataclass(frozen=True, slots=True)
class WorkspaceSyncReconcileRequest:
    """Request to reconcile local and committed workspace state."""

    workspace_binding_id: str
    machine_id: str
    observed_generation: int
    exclusion_policy_digest: str
    manifest_root: str
    protocol: WorkspaceSyncProtocolRange


@dataclass(frozen=True, slots=True)
class WorkspaceSyncChangeOptions:
    """Options for reading ordered committed workspace changes."""

    reader_version: int
    cursor: str | None = None
    limit: int | None = None


WorkspaceSyncCapability = Literal[
    "atomic_generation_commit",
    "bounded_manifest_pages",
    "content_digest_verification",
    "explicit_reconciliation",
    "ordered_generation_changes",
    "policy_bound_admission",
]


@dataclass(frozen=True, slots=True)
class WorkspaceBindingCreateRequest:
    """Canonical identity tuple used to create or adopt a workspace binding."""

    workspace_id: str
    project_id: str
    local_instance_id: str
    machine_id: str
    exclusion_policy_digest: str
    excluded_prefixes: list[str]


@dataclass(frozen=True, slots=True)
class WorkspaceBinding:
    """Exact authenticated binding between a local project and a Runa machine."""

    binding_id: str
    workspace_id: str
    project_id: str
    local_instance_id: str
    machine_id: str
    remote_root: str
    exclusion_policy_digest: str
    active_generation: int
    active_manifest_root: str
    binding_epoch: int
    minimum_reader: int
    minimum_writer: int
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class WorkspaceBindingLookup:
    """Full identity proof required to read a canonical workspace binding."""

    workspace_id: str
    project_id: str
    local_instance_id: str
    machine_id: str
    exclusion_policy_digest: str


@dataclass(frozen=True, slots=True)
class WorkspaceSyncChunkRef:
    """Content-addressed reference to one bounded workspace chunk."""

    digest: str
    byte_length: int


@dataclass(frozen=True, slots=True)
class WorkspaceSyncManifestEntry:
    """Portable manifest entry for one workspace path."""

    path: str
    kind: Literal["directory", "file", "symlink"]
    byte_length: int
    executable: bool
    chunks: list[WorkspaceSyncChunkRef]
    link_target: str | None


@dataclass(frozen=True, slots=True)
class WorkspaceSyncSession:
    """Observed state of one bounded workspace synchronization session."""

    id: str
    workspace_id: str
    machine_id: str
    base_generation: int
    exclusion_policy_digest: str
    selected_protocol: Literal[1, 2]
    capabilities: tuple[WorkspaceSyncCapability, ...]
    state: Literal["staging", "committed", "conflicted", "expired"]
    manifest_entry_count: int
    manifest_encoded_bytes: int
    content_bytes: int
    expires_at: str
    created_at: str
    updated_at: str
    last_page_index: int | None = None
    committed_generation: int | None = None
    committed_manifest_root: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceSyncManifestReceipt:
    """Receipt for one accepted workspace manifest page."""

    sync: WorkspaceSyncSession
    page_index: int
    page_digest: str
    missing_digests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkspaceSyncChunkReceipt:
    """Receipt for one verified content-addressed workspace chunk."""

    selected_protocol: Literal[1, 2]
    digest: str
    byte_length: int
    stored: bool


@dataclass(frozen=True, slots=True)
class WorkspaceSyncChunkContent:
    """Private decoded carrier for a digest-verified workspace chunk."""

    selected_protocol: Literal[1, 2]
    digest: str
    byte_length: int
    minimum_reader: int
    content: bytes


@dataclass(frozen=True, slots=True)
class WorkspaceSyncCommitReceipt:
    """Receipt for one atomically committed workspace generation."""

    selected_protocol: Literal[1, 2]
    state: Literal["committed"]
    generation: int
    manifest_root: str
    committed_at: str
    minimum_reader: int
    minimum_writer: int


@dataclass(frozen=True, slots=True)
class WorkspaceSyncChangeItem:
    """One ordered change in a committed workspace generation."""

    generation: int
    operation: Literal["revision", "upsert", "delete"]
    path: str | None
    entry: WorkspaceSyncManifestEntry | None
    manifest_root: str
    exclusion_policy_digest: str
    committed_at: str
    minimum_reader: int
    minimum_writer: int


@dataclass(frozen=True, slots=True)
class WorkspaceSyncChangePage:
    """One bounded page of ordered committed workspace changes."""

    selected_protocol: Literal[1, 2]
    items: tuple[WorkspaceSyncChangeItem, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class WorkspaceSyncReconcileReceipt:
    """Receipt describing workspace convergence or required reconciliation."""

    selected_protocol: Literal[1, 2]
    status: Literal["converged", "reconciliation_required"]
    active_generation: int
    active_manifest_root: str
    exclusion_policy_digest: str


WorkspaceSyncData = TypeVar("WorkspaceSyncData")


@dataclass(frozen=True, slots=True)
class WorkspaceSyncEnvelope(Generic[WorkspaceSyncData]):
    """Protocol and capability evidence wrapping workspace synchronization data."""

    request_id: str
    selected_protocol: Literal[1, 2]
    capabilities: tuple[WorkspaceSyncCapability, ...]
    data: WorkspaceSyncData


@dataclass(frozen=True, slots=True)
class MachineCreateRequest:
    """Non-secret machine creation status and recovery action."""

    id: str
    machine_id: str
    state: Literal[
        "prepared",
        "in_progress",
        "unknown",
        "provider_succeeded",
        "settled",
        "terminal_failed",
    ]
    retryable: bool
    action: Literal["retry_create", "reconcile", "wait", "none"]
    updated_at: str


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

    # `repr=False` is what makes the docstring above true by construction. The
    # URL's query token IS the capability, so a default repr hands it to every
    # log line, traceback, and locals-capturing reporter that touches this
    # object. Same mitigation as `TerminalConnectionGrant.connect_token`.
    url: str = field(repr=False)


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
        id: Canonical public workspace UUID used by synchronization APIs.
        usage: Estimated workspace usage.
    Examples:
        See ``REF-EX-ASSIGNEDWORKSPACE`` and ``TC-091-09``.
    """

    assigned: Literal[True]
    id: str
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

"""Canonical safe, public-surface-only API reference examples.

The examples are compiled by the documentation gate and can be invoked with
synthetic public-shaped fixtures without credentials, DNS, or network access.
"""

from __future__ import annotations

from cuna import (
    UNSET,
    Acknowledgement,
    AgentSession,
    AgentSessionAuth,
    AgentSessionAuthEvidenceClass,
    AgentSessionAuthMode,
    AgentSessionAuthState,
    AgentSessionCreateOptions,
    AgentSessionDesiredState,
    AgentSessionListOptions,
    AgentSessionPage,
    AgentSessionProcessState,
    AgentSessionRequestState,
    AgentSessionsManager,
    AssignedWorkspace,
    AsyncAgentSessionsManager,
    AsyncCapabilitiesManager,
    AsyncCuna,
    AsyncMachineCreatesManager,
    AsyncRecordsManager,
    AsyncSession,
    AsyncSessionsManager,
    AsyncWorkspaceBindingsManager,
    AsyncWorkspaceSyncManager,
    CapabilitiesManager,
    Capability,
    CapabilityAvailability,
    CapabilityInteraction,
    CapabilityMutationClass,
    CapabilityScope,
    CapabilitySnapshot,
    CapabilitySurface,
    Cuna,
    EstimatedUsage,
    ExecOptions,
    ExecResult,
    MachineCreateRequest,
    MachineCreatesManager,
    Me,
    OpenSessionResult,
    OutboundPolicy,
    OutboundPolicyMode,
    Record,
    RecordsManager,
    Session,
    SessionAgent,
    SessionCreateOptions,
    SessionsManager,
    SessionSnapshot,
    SessionStatus,
    TerminalConnectionAvailability,
    TerminalConnectionCapability,
    TerminalConnectionCapabilityName,
    TerminalConnectionCreateOptions,
    TerminalConnectionGrant,
    UnassignedWorkspace,
    UnsetType,
    WorkspaceBinding,
    WorkspaceBindingCreateRequest,
    WorkspaceBindingLookup,
    WorkspaceBindingsManager,
    WorkspaceSyncBeginRequest,
    WorkspaceSyncCapability,
    WorkspaceSyncChangeItem,
    WorkspaceSyncChangeOptions,
    WorkspaceSyncChangePage,
    WorkspaceSyncChunkReceipt,
    WorkspaceSyncChunkRef,
    WorkspaceSyncCommitReceipt,
    WorkspaceSyncCommitRequest,
    WorkspaceSyncEnvelope,
    WorkspaceSyncManager,
    WorkspaceSyncManifestEntry,
    WorkspaceSyncManifestPageRequest,
    WorkspaceSyncManifestReceipt,
    WorkspaceSyncProtocolRange,
    WorkspaceSyncReconcileReceipt,
    WorkspaceSyncReconcileRequest,
    WorkspaceSyncSession,
)
from cuna.errors import (
    ApiError,
    ApiProblem,
    CommandError,
    ConfigError,
    CunaError,
    ProblemAction,
    WorkspaceSyncProblem,
)


def cuna(client: Cuna) -> None:
    account = client.me()
    sessions = client.sessions
    records = client.records
    capabilities = client.capabilities
    del account, sessions, records, capabilities


def capabilities_manager(manager: CapabilitiesManager) -> None:
    snapshot = manager.get(CapabilityScope.ACCOUNT)
    del snapshot


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


async def async_cuna(client: AsyncCuna) -> None:
    account = await client.me()
    sessions = client.sessions
    records = client.records
    capabilities = client.capabilities
    del account, sessions, records, capabilities


async def async_capabilities_manager(manager: AsyncCapabilitiesManager) -> None:
    snapshot = await manager.get(CapabilityScope.ACCOUNT)
    del snapshot


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


def capability(value: Capability) -> CapabilityAvailability:
    return value.availability


def capability_availability() -> CapabilityAvailability:
    return CapabilityAvailability.SUPPORTED


def capability_interaction() -> CapabilityInteraction:
    return CapabilityInteraction.READ_ONLY


def capability_mutation_class() -> CapabilityMutationClass:
    return CapabilityMutationClass.NONE


def capability_scope() -> CapabilityScope:
    return CapabilityScope.ACCOUNT


def capability_snapshot(value: CapabilitySnapshot) -> tuple[Capability, ...]:
    return value.capabilities


def capability_surface() -> CapabilitySurface:
    return CapabilitySurface.SDK


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


def outbound_policy() -> OutboundPolicy:
    return OutboundPolicy(OutboundPolicyMode.DENYLIST, ["tracking.example.com"])


def outbound_policy_mode() -> OutboundPolicyMode:
    return OutboundPolicyMode.ALLOWLIST


def record(value: Record) -> str:
    return value.summary


def session_agent() -> SessionAgent:
    return SessionAgent.CODEX


def session_create_options() -> SessionCreateOptions:
    return SessionCreateOptions(
        agent=SessionAgent.CODEX,
        memory_mib=2048,
    )


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


def agent_session(value: AgentSession) -> str:
    return value.workspace_binding_id or value.id


def agent_session_auth(value: AgentSessionAuth) -> AgentSessionAuthState:
    return value.state


def agent_session_auth_evidence_class() -> AgentSessionAuthEvidenceClass:
    return AgentSessionAuthEvidenceClass.PROVIDER_CLI_LOGIN_STATUS


def agent_session_auth_mode() -> AgentSessionAuthMode:
    return AgentSessionAuthMode.INTERACTIVE_LOGIN


def agent_session_auth_state() -> AgentSessionAuthState:
    return AgentSessionAuthState.AUTHENTICATED


def agent_session_create_options(value: AgentSessionCreateOptions) -> str:
    return value.workspace_binding_id


def agent_session_desired_state() -> AgentSessionDesiredState:
    return AgentSessionDesiredState.RUNNING


def agent_session_list_options(value: AgentSessionListOptions) -> int | None:
    return value.limit


def agent_session_page(value: AgentSessionPage) -> tuple[AgentSession, ...]:
    return value.items


def agent_session_process_state() -> AgentSessionProcessState:
    return AgentSessionProcessState.UNKNOWN


def agent_session_request_state() -> AgentSessionRequestState:
    return AgentSessionRequestState.LAUNCH_PENDING


def agent_sessions_manager(manager: AgentSessionsManager) -> None:
    session = manager.get("22222222-2222-4222-8222-222222222222")
    authentication = manager.agent_auth(session)
    del authentication


async def async_agent_sessions_manager(manager: AsyncAgentSessionsManager) -> None:
    session = await manager.get("22222222-2222-4222-8222-222222222222")
    authentication = await manager.agent_auth(session)
    del authentication


def machine_create_request(value: MachineCreateRequest) -> str:
    return value.state


def machine_creates_manager(manager: MachineCreatesManager) -> None:
    del manager


async def async_machine_creates_manager(manager: AsyncMachineCreatesManager) -> None:
    del manager


def terminal_connection_availability() -> TerminalConnectionAvailability:
    return TerminalConnectionAvailability.UNKNOWN


def terminal_connection_capability(
    value: TerminalConnectionCapability,
) -> TerminalConnectionCapabilityName:
    return value.name


def terminal_connection_capability_name() -> TerminalConnectionCapabilityName:
    return TerminalConnectionCapabilityName.ACKNOWLEDGEMENT


def terminal_connection_create_options(value: TerminalConnectionCreateOptions) -> str:
    return value.client_instance_id


def terminal_connection_grant(value: TerminalConnectionGrant) -> str:
    return value.terminal_session_id


def workspace_binding(value: WorkspaceBinding) -> str:
    return value.binding_id


def workspace_binding_create_request(value: WorkspaceBindingCreateRequest) -> str:
    return value.workspace_id


def workspace_binding_lookup(value: WorkspaceBindingLookup) -> str:
    return value.workspace_id


def workspace_bindings_manager(manager: WorkspaceBindingsManager) -> None:
    del manager


async def async_workspace_bindings_manager(manager: AsyncWorkspaceBindingsManager) -> None:
    del manager


def workspace_sync_begin_request(value: WorkspaceSyncBeginRequest) -> str:
    return value.workspace_binding_id


def workspace_sync_capability(value: WorkspaceSyncCapability) -> WorkspaceSyncCapability:
    return value


def workspace_sync_change_item(value: WorkspaceSyncChangeItem) -> int:
    return value.generation


def workspace_sync_change_options(value: WorkspaceSyncChangeOptions) -> int:
    return value.reader_version


def workspace_sync_change_page(value: WorkspaceSyncChangePage) -> int:
    return value.selected_protocol


def workspace_sync_chunk_receipt(value: WorkspaceSyncChunkReceipt) -> str:
    return value.digest


def workspace_sync_chunk_ref(value: WorkspaceSyncChunkRef) -> str:
    return value.digest


def workspace_sync_commit_receipt(value: WorkspaceSyncCommitReceipt) -> int:
    return value.generation


def workspace_sync_commit_request(value: WorkspaceSyncCommitRequest) -> int:
    return value.expected_generation


def workspace_sync_envelope(value: WorkspaceSyncEnvelope[WorkspaceSyncSession]) -> str:
    return value.request_id


def workspace_sync_manager(manager: WorkspaceSyncManager) -> None:
    del manager


async def async_workspace_sync_manager(manager: AsyncWorkspaceSyncManager) -> None:
    del manager


def workspace_sync_manifest_entry(value: WorkspaceSyncManifestEntry) -> str:
    return value.path


def workspace_sync_manifest_page_request(value: WorkspaceSyncManifestPageRequest) -> int:
    return value.page_index


def workspace_sync_manifest_receipt(value: WorkspaceSyncManifestReceipt) -> str:
    return value.page_digest


def workspace_sync_protocol_range(value: WorkspaceSyncProtocolRange) -> int:
    return value.maximum


def workspace_sync_reconcile_receipt(value: WorkspaceSyncReconcileReceipt) -> str:
    return value.status


def workspace_sync_reconcile_request(value: WorkspaceSyncReconcileRequest) -> str:
    return value.workspace_binding_id


def workspace_sync_session(value: WorkspaceSyncSession) -> str:
    return value.id


def api_error(error: ApiError) -> int:
    return error.status


def api_problem(error: ApiProblem) -> str:
    return error.code


def command_error(error: CommandError) -> str:
    return error.code


def config_error(error: ConfigError) -> str:
    return error.message


def problem_action() -> ProblemAction:
    return ProblemAction.NONE


def cuna_error(error: CunaError) -> str:
    return error.code


def workspace_sync_problem(error: WorkspaceSyncProblem) -> int | None:
    return error.selected_protocol

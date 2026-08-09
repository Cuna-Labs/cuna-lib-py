from runa import (
    AgentAuthenticationState,
    AgentAuthenticationStatus,
    AsyncRuna,
    Capability,
    CapabilityAvailability,
    CapabilityScope,
    CapabilitySnapshot,
    ExecOptions,
    OutboundPolicy,
    OutboundPolicyMode,
    Runa,
    SessionAgent,
    SessionCreateOptions,
    SessionStatus,
    TerminalConnectionCreateOptions,
    TerminalConnectionGrant,
)


def sync_use(client: Runa) -> None:
    capabilities: CapabilitySnapshot = client.capabilities.get(CapabilityScope.ACCOUNT)
    capability: Capability | None = next(iter(capabilities.capabilities), None)
    session = client.sessions.create(
        "typed",
        SessionCreateOptions(
            agent=SessionAgent.CODEX,
            background=True,
            vcpus=2,
            memory_mib=1024,
            allowed_hosts=["example.com"],
            runtime_port=8080,
        ),
    )
    client.sessions.create(
        "policy",
        SessionCreateOptions(
            outbound_policy=OutboundPolicy(OutboundPolicyMode.DENYLIST, ["tracking.example.com"])
        ),
    )
    result = session.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    terminal: TerminalConnectionGrant = client.agent_sessions.create_terminal_connection(
        "00000000-0000-0000-0000-000000000000",
        TerminalConnectionCreateOptions("terminal-connect-typed", "consumer.test"),
    )
    authentication: AgentAuthenticationStatus = session.authentication_status()
    status: SessionStatus = session.snapshot.status
    exit_code: int = result.exit_code
    _ = (
        status,
        exit_code,
        authentication.state is AgentAuthenticationState.AUTHENTICATED,
        client.records.list(),
        client.me(),
        capability is not None and capability.availability is CapabilityAvailability.SUPPORTED,
        terminal.protocol,
    )


async def async_use(client: AsyncRuna) -> None:
    capabilities: CapabilitySnapshot = await client.capabilities.get(CapabilityScope.ACCOUNT)
    session = await client.sessions.get("00000000-0000-0000-0000-000000000000")
    result = await session.exec("python --version", ExecOptions())
    terminal: TerminalConnectionGrant = await client.agent_sessions.create_terminal_connection(
        "00000000-0000-0000-0000-000000000000",
        TerminalConnectionCreateOptions("terminal-connect-typed", "consumer.test"),
    )
    authentication: AgentAuthenticationStatus = await session.authentication_status()
    exit_code: int = result.exit_code
    _ = (
        exit_code,
        authentication.method,
        await client.records.list(),
        await client.me(),
        capabilities.etag,
        terminal.expires_at,
    )

from runa import (
    AsyncRuna,
    ExecOptions,
    Runa,
    SessionAgent,
    SessionCreateOptions,
    SessionStatus,
)


def sync_use(client: Runa) -> None:
    session = client.sessions.create(
        "typed",
        SessionCreateOptions(
            agent=SessionAgent.CODEX,
            vcpus=2,
            memory_mib=1024,
            allowed_hosts=["example.com"],
            runtime_port=8080,
        ),
    )
    result = session.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    status: SessionStatus = session.snapshot.status
    exit_code: int = result.exit_code
    _ = (status, exit_code, client.records.list(), client.me())


async def async_use(client: AsyncRuna) -> None:
    session = await client.sessions.get("00000000-0000-0000-0000-000000000000")
    result = await session.exec("python --version", ExecOptions())
    exit_code: int = result.exit_code
    _ = (exit_code, await client.records.list(), await client.me())

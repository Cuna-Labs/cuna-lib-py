"""List and manage durable AgentSession resources asynchronously."""

import asyncio
import uuid

from runa import AgentSessionCreateOptions, AsyncRuna, SessionAgent


async def main() -> None:
    machine_id = "11111111-1111-4111-8111-111111111111"
    async with AsyncRuna() as client:
        created = await client.agent_sessions.create(
            machine_id,
            AgentSessionCreateOptions(
                idempotency_key=str(uuid.uuid4()),
                agent=SessionAgent.CODEX,
                cwd="/workspace/project",
                workspace_binding_id="77777777-7777-4777-8777-777777777777",
                workspace_generation=7,
            ),
        )
        await client.agent_sessions.terminate(created.id)


asyncio.run(main())

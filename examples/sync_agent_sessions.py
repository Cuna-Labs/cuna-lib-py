"""List and manage durable AgentSession resources synchronously."""

import uuid

from runa import AgentSessionCreateOptions, Runa, SessionAgent

machine_id = "11111111-1111-4111-8111-111111111111"
with Runa() as client:
    client.agent_sessions.list(machine_id)
    created = client.agent_sessions.create(
        machine_id,
        AgentSessionCreateOptions(
            idempotency_key=str(uuid.uuid4()),
            agent=SessionAgent.CODEX,
            cwd="/workspace/project",
            name="review",
        ),
    )
    client.agent_sessions.rename(created.id, "review-api")
    client.agent_sessions.terminate(created.id)

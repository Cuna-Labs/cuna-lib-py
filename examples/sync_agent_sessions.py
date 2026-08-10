"""List and manage durable AgentSession resources synchronously."""

import uuid

from cuna import AgentSessionCreateOptions, Cuna, SessionAgent

machine_id = "11111111-1111-4111-8111-111111111111"
with Cuna() as client:
    client.agent_sessions.list(machine_id)
    created = client.agent_sessions.create(
        machine_id,
        AgentSessionCreateOptions(
            idempotency_key=str(uuid.uuid4()),
            agent=SessionAgent.CODEX,
            cwd="/workspace/project",
            workspace_binding_id="77777777-7777-4777-8777-777777777777",
            workspace_generation=7,
            name="review",
        ),
    )
    client.agent_sessions.rename(created.id, "review-api")
    client.agent_sessions.terminate(created.id)

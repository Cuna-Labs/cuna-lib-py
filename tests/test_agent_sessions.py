from __future__ import annotations

from copy import deepcopy

import pytest

from runa import (
    AgentSessionAuthMode,
    AgentSessionCreateOptions,
    AgentSessionListOptions,
    AgentSessionProcessState,
    AsyncRuna,
    Runa,
    SessionAgent,
)
from runa.errors import ApiError, ConfigError

from .support import AsyncRecorder, SyncRecorder, json_response

MACHINE_ID = "11111111-1111-4111-8111-111111111111"
AGENT_SESSION_ID = "22222222-2222-4222-8222-222222222222"


def payload(**overrides: object) -> dict[str, object]:
    return {
        "id": AGENT_SESSION_ID,
        "machine_id": MACHINE_ID,
        "name": "review",
        "agent": "codex",
        "cwd": "/workspace/repo",
        "auth_mode": "interactive_login",
        "desired_state": "running",
        "request_state": "launched",
        "process_state": "running",
        "process_epoch": "33333333-3333-4333-8333-333333333333",
        "runtime_observed_at": "2026-08-08T12:00:00Z",
        "row_version": 3,
        "created_at": "2026-08-08T11:59:00Z",
        "updated_at": "2026-08-08T12:00:00Z",
        **overrides,
    }


def response(request, _context):
    if request.operation_key == "agentSessions.list":
        return json_response(200, {"items": [payload()], "next_cursor": "next"})
    if request.operation_key == "agentSessions.create":
        return json_response(201, payload(request_state="launch_pending", process_state="unknown"))
    if request.operation_key == "agentSessions.rename":
        return json_response(200, payload(name="renamed"))
    if request.operation_key == "agentSessions.terminate":
        return json_response(200, payload(desired_state="terminated"))
    return json_response(200, payload())


@pytest.mark.hermetic
@pytest.mark.contract
def test_sync_agent_sessions_preserve_authoritative_wire_contract() -> None:
    recorder = SyncRecorder(response)
    client = Runa(api_key="runa_sk_test", transport=recorder)
    page = client.agent_sessions.list(
        MACHINE_ID, AgentSessionListOptions(limit=25, cursor="opaque")
    )
    assert page.next_cursor == "next"
    assert page.items[0].process_state is AgentSessionProcessState.RUNNING
    client.agent_sessions.create(
        MACHINE_ID,
        AgentSessionCreateOptions(
            idempotency_key="agent-session-create-1",
            agent=SessionAgent.CODEX,
            cwd="/workspace/repo",
            name="review",
        ),
    )
    client.agent_sessions.get(AGENT_SESSION_ID)
    client.agent_sessions.rename(AGENT_SESSION_ID, "renamed")
    client.agent_sessions.terminate(AGENT_SESSION_ID)

    requests = [call[0] for call in recorder.calls]
    assert requests[0].relative_path == (
        f"/v1/sessions/{MACHINE_ID}/agent-sessions?limit=25&cursor=opaque"
    )
    assert requests[1].headers["Idempotency-Key"] == "agent-session-create-1"
    assert dict(requests[1].body or {}) == {
        "agent": "codex",
        "cwd": "/workspace/repo",
        "name": "review",
    }
    assert [request.method for request in requests] == ["GET", "POST", "GET", "PATCH", "POST"]
    client.close()


@pytest.mark.hermetic
@pytest.mark.contract
@pytest.mark.asyncio
async def test_async_agent_sessions_match_sync_wire_behavior() -> None:
    recorder = AsyncRecorder(response)
    client = AsyncRuna._with_transport(api_key="runa_sk_test", transport=recorder)
    page = await client.agent_sessions.list(MACHINE_ID)
    created = await client.agent_sessions.create(
        MACHINE_ID,
        AgentSessionCreateOptions(
            idempotency_key="agent-session-create-2",
            agent=SessionAgent.CODEX,
            cwd="/workspace/repo",
        ),
    )
    assert page.items[0].machine_id == MACHINE_ID
    assert created.auth_mode is AgentSessionAuthMode.INTERACTIVE_LOGIN
    assert recorder.calls[1][0].headers["Idempotency-Key"] == "agent-session-create-2"
    await client.close()


@pytest.mark.hermetic
@pytest.mark.contract
def test_agent_session_inputs_and_responses_fail_closed() -> None:
    calls = 0

    def malformed(_request, _context):
        nonlocal calls
        calls += 1
        value = deepcopy(payload())
        value["unknown_field"] = True
        return json_response(200, value)

    client = Runa(api_key="runa_sk_test", transport=SyncRecorder(malformed))
    with pytest.raises(ConfigError):
        client.agent_sessions.create(
            MACHINE_ID,
            AgentSessionCreateOptions(
                idempotency_key="short",
                agent=SessionAgent.CODEX,
                cwd="/workspace/repo",
            ),
        )
    assert calls == 0
    with pytest.raises(ApiError) as error:
        client.agent_sessions.get(AGENT_SESSION_ID)
    assert error.value.code == "malformed_response"
    assert calls == 1
    client.close()

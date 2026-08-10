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
    TerminalConnectionAvailability,
    TerminalConnectionCapabilityName,
    TerminalConnectionCreateOptions,
)
from runa.errors import ApiError, ConfigError, ProblemAction

from .support import AsyncRecorder, SyncRecorder, json_response

MACHINE_ID = "11111111-1111-4111-8111-111111111111"
AGENT_SESSION_ID = "22222222-2222-4222-8222-222222222222"
WORKSPACE_ID = "77777777-7777-4777-8777-777777777777"
WORKSPACE_GENERATION = 7
TERMINAL_SESSION_ID = "44444444-4444-4444-8444-444444444444"
RESUME_HANDLE = "55555555-5555-4555-8555-555555555555"


def terminal_payload(**overrides: object) -> dict[str, object]:
    return {
        "terminal_session_id": TERMINAL_SESSION_ID,
        "resume_handle": RESUME_HANDLE,
        "connect_url": (
            f"wss://api.runacode.io/v1/terminal-connections/{TERMINAL_SESSION_ID}/stream"
        ),
        "connect_token": "runa_tc_" + "A" * 43,
        "protocol": "runa.terminal.v1",
        "capabilities": [
            {"name": name, "availability": "supported"}
            for name in (
                "acknowledgement",
                "heartbeat",
                "live_resize",
                "resume",
                "signals",
            )
        ],
        "expires_at": "2026-08-08T12:05:00Z",
        **overrides,
    }


def payload(**overrides: object) -> dict[str, object]:
    return {
        "id": AGENT_SESSION_ID,
        "machine_id": MACHINE_ID,
        "workspace_binding_id": WORKSPACE_ID,
        "workspace_generation": WORKSPACE_GENERATION,
        "name": "review",
        "agent": "codex",
        "cwd": "/workspace/repo",
        "auth_mode": "interactive_login",
        "desired_state": "running",
        "request_state": "launched",
        "process_state": "running",
        "process_epoch": "33333333-3333-4333-8333-333333333333",
        "runtime_observed_at": "2026-08-08T12:00:00Z",
        "runtime_expires_at": "2026-08-08T12:00:30Z",
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
    if request.operation_key == "agentSessions.createTerminalConnection":
        return json_response(201, terminal_payload())
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
    assert page.items[0].workspace_binding_id == WORKSPACE_ID
    assert page.items[0].workspace_generation == WORKSPACE_GENERATION
    assert page.items[0].runtime_expires_at == "2026-08-08T12:00:30Z"
    client.agent_sessions.create(
        MACHINE_ID,
        AgentSessionCreateOptions(
            idempotency_key="agent-session-create-1",
            agent=SessionAgent.CODEX,
            cwd="/workspace/repo",
            workspace_binding_id=WORKSPACE_ID,
            workspace_generation=WORKSPACE_GENERATION,
            name="review",
        ),
    )
    client.agent_sessions.get(AGENT_SESSION_ID)
    client.agent_sessions.rename(AGENT_SESSION_ID, "renamed")
    client.agent_sessions.terminate(AGENT_SESSION_ID)
    grant = client.agent_sessions.create_terminal_connection(
        AGENT_SESSION_ID,
        TerminalConnectionCreateOptions(
            idempotency_key="terminal-connect-1",
            client_instance_id="desktop.test:1",
            resume_handle=RESUME_HANDLE,
        ),
    )
    assert grant.terminal_session_id == TERMINAL_SESSION_ID
    assert grant.capabilities[0].name is TerminalConnectionCapabilityName.ACKNOWLEDGEMENT
    assert grant.capabilities[0].availability is TerminalConnectionAvailability.SUPPORTED
    assert "runa_tc_" not in repr(grant)

    requests = [call[0] for call in recorder.calls]
    assert requests[0].relative_path == (
        f"/v1/sessions/{MACHINE_ID}/agent-sessions?limit=25&cursor=opaque"
    )
    assert requests[1].headers["Idempotency-Key"] == "agent-session-create-1"
    assert dict(requests[1].body or {}) == {
        "agent": "codex",
        "cwd": "/workspace/repo",
        "workspace_binding_id": WORKSPACE_ID,
        "workspace_generation": WORKSPACE_GENERATION,
        "name": "review",
    }
    assert requests[-1].relative_path == (
        f"/v1/agent-sessions/{AGENT_SESSION_ID}/terminal-connections"
    )
    assert requests[-1].headers["Idempotency-Key"] == "terminal-connect-1"
    assert dict(requests[-1].body or {}) == {
        "client_instance_id": "desktop.test:1",
        "protocol": "runa.terminal.v1",
        "resume_handle": RESUME_HANDLE,
    }
    assert [request.method for request in requests] == [
        "GET",
        "POST",
        "GET",
        "PATCH",
        "POST",
        "POST",
    ]
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
            workspace_binding_id=WORKSPACE_ID,
            workspace_generation=WORKSPACE_GENERATION,
        ),
    )
    assert page.items[0].machine_id == MACHINE_ID
    assert created.auth_mode is AgentSessionAuthMode.INTERACTIVE_LOGIN
    assert recorder.calls[1][0].headers["Idempotency-Key"] == "agent-session-create-2"
    grant = await client.agent_sessions.create_terminal_connection(
        AGENT_SESSION_ID,
        TerminalConnectionCreateOptions(
            idempotency_key="terminal-connect-2",
            client_instance_id="async.client",
        ),
    )
    assert grant.protocol == "runa.terminal.v1"
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
                workspace_binding_id=WORKSPACE_ID,
                workspace_generation=WORKSPACE_GENERATION,
            ),
        )
    with pytest.raises(ConfigError):
        client.agent_sessions.create(
            MACHINE_ID,
            AgentSessionCreateOptions(
                idempotency_key="agent-session-create-3",
                agent=SessionAgent.CODEX,
                cwd="/workspace/repo",
                workspace_binding_id=WORKSPACE_ID,
                workspace_generation=0,
            ),
        )
    assert calls == 0
    with pytest.raises(ApiError) as error:
        client.agent_sessions.get(AGENT_SESSION_ID)
    assert error.value.code == "malformed_response"
    assert calls == 1
    client.close()

    invalid_lease = Runa(
        api_key="runa_sk_test",
        transport=SyncRecorder(
            lambda _request, _context: json_response(200, payload(runtime_expires_at="not-a-date"))
        ),
    )
    with pytest.raises(ApiError) as lease_error:
        invalid_lease.agent_sessions.get(AGENT_SESSION_ID)
    assert lease_error.value.code == "malformed_response"
    invalid_lease.close()

    for partial in (
        payload(workspace_binding_id=None),
        payload(workspace_generation=None),
        payload(workspace_generation=0),
    ):
        partial = {key: value for key, value in partial.items() if value is not None}
        invalid_workspace = Runa(
            api_key="runa_sk_test",
            transport=SyncRecorder(
                lambda _request, _context, value=partial: json_response(200, value)
            ),
        )
        with pytest.raises(ApiError) as workspace_error:
            invalid_workspace.agent_sessions.get(AGENT_SESSION_ID)
        assert workspace_error.value.code == "malformed_response"
        invalid_workspace.close()

    legacy_payload = payload()
    del legacy_payload["workspace_binding_id"]
    del legacy_payload["workspace_generation"]
    legacy = Runa(
        api_key="runa_sk_test",
        transport=SyncRecorder(lambda _request, _context: json_response(200, legacy_payload)),
    )
    legacy_session = legacy.agent_sessions.get(AGENT_SESSION_ID)
    assert legacy_session.workspace_binding_id is None
    assert legacy_session.workspace_generation is None
    legacy.close()

    renamed_field_payload = payload()
    renamed_field_payload["workspace_id"] = renamed_field_payload.pop("workspace_binding_id")
    renamed_field = Runa(
        api_key="runa_sk_test",
        transport=SyncRecorder(
            lambda _request, _context: json_response(200, renamed_field_payload)
        ),
    )
    with pytest.raises(ApiError) as renamed_field_error:
        renamed_field.agent_sessions.get(AGENT_SESSION_ID)
    assert renamed_field_error.value.code == "malformed_response"
    renamed_field.close()


@pytest.mark.hermetic
@pytest.mark.contract
@pytest.mark.parametrize(
    "substitution",
    [
        {"workspace_binding_id": "88888888-8888-4888-8888-888888888888"},
        {"workspace_generation": WORKSPACE_GENERATION + 1},
    ],
)
def test_agent_session_create_rejects_substituted_workspace_authority(
    substitution: dict[str, object],
) -> None:
    client = Runa(
        api_key="runa_sk_test",
        transport=SyncRecorder(
            lambda _request, _context: json_response(
                201,
                payload(**substitution),
            )
        ),
    )
    with pytest.raises(ApiError) as error:
        client.agent_sessions.create(
            MACHINE_ID,
            AgentSessionCreateOptions(
                idempotency_key="agent-session-create-4",
                agent=SessionAgent.CODEX,
                cwd="/workspace/repo",
                workspace_binding_id=WORKSPACE_ID,
                workspace_generation=WORKSPACE_GENERATION,
            ),
        )
    assert error.value.code == "malformed_response"
    client.close()


@pytest.mark.hermetic
@pytest.mark.contract
def test_terminal_connection_request_response_and_problem_fail_closed() -> None:
    recorder = SyncRecorder(response)
    client = Runa(api_key="runa_sk_test", transport=recorder)
    for options in (
        TerminalConnectionCreateOptions("short", "client"),
        TerminalConnectionCreateOptions("terminal-connect-3", "bad client"),
        TerminalConnectionCreateOptions("terminal-connect-3", "client", "not-a-uuid"),
    ):
        with pytest.raises(ConfigError):
            client.agent_sessions.create_terminal_connection(AGENT_SESSION_ID, options)
    assert recorder.calls == []

    def malformed(_request, _context):
        return json_response(201, terminal_payload(provider="internal"))

    recorder.responder = malformed
    with pytest.raises(ApiError) as malformed_error:
        client.agent_sessions.create_terminal_connection(
            AGENT_SESSION_ID,
            TerminalConnectionCreateOptions("terminal-connect-4", "client"),
        )
    assert malformed_error.value.code == "malformed_response"

    def problem(_request, _context):
        return json_response(
            409,
            {
                "type": (
                    "https://api.runacode.io/problems/terminal_connection_idempotency_conflict"
                ),
                "title": "Idempotency conflict",
                "status": 409,
                "code": "terminal_connection_idempotency_conflict",
                "request_id": "66666666-6666-4666-8666-666666666666",
                "retryable": False,
                "action": "none",
            },
        )

    recorder.responder = problem
    with pytest.raises(ApiError) as conflict:
        client.agent_sessions.create_terminal_connection(
            AGENT_SESSION_ID,
            TerminalConnectionCreateOptions("terminal-connect-4", "client"),
        )
    assert conflict.value.problem is not None
    assert conflict.value.problem.code == "terminal_connection_idempotency_conflict"
    assert conflict.value.problem.action is ProblemAction.NONE
    assert str(conflict.value) == "The Runa API request failed."


@pytest.mark.hermetic
@pytest.mark.contract
@pytest.mark.parametrize(
    "mutation",
    [
        {"protocol": "future"},
        {"connect_token": "runa_tc_short"},
        {"connect_url": "wss://api.runacode.io/v1/terminal-connections/wrong/stream"},
        {"capabilities": [{"name": "acknowledgement", "availability": "supported"}] * 5},
        {
            "capabilities": [
                {"name": "acknowledgement", "availability": "future"},
                {"name": "heartbeat", "availability": "supported"},
                {"name": "live_resize", "availability": "supported"},
                {"name": "resume", "availability": "supported"},
                {"name": "signals", "availability": "supported"},
            ]
        },
    ],
)
def test_terminal_connection_grant_rejects_semantic_drift(
    mutation: dict[str, object],
) -> None:
    recorder = SyncRecorder(
        lambda _request, _context: json_response(201, terminal_payload(**mutation))
    )
    client = Runa(api_key="runa_sk_test", transport=recorder)
    with pytest.raises(ApiError) as malformed:
        client.agent_sessions.create_terminal_connection(
            AGENT_SESSION_ID,
            TerminalConnectionCreateOptions("terminal-connect-5", "client"),
        )
    assert malformed.value.code == "malformed_response"

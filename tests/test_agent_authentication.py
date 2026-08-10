from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cuna import (
    AgentSessionAuthEvidenceClass,
    AgentSessionAuthState,
    AsyncCuna,
    Cuna,
)
from cuna._internal.contract.bridge import DecodeFailure, decode_for_operation
from cuna._internal.transport import PreparedRequest, RawResponse, RequestContext
from cuna.errors import ApiError

from .support import AsyncRecorder, SyncRecorder, json_response
from .test_agent_sessions import AGENT_SESSION_ID
from .test_agent_sessions import payload as agent_session_payload

OBSERVATION_ID = "66666666-6666-4666-8666-666666666666"
PROCESS_EPOCH = "33333333-3333-4333-8333-333333333333"
SIBLING_ID = "99999999-9999-4999-8999-999999999999"


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def auth_payload(**overrides: object) -> dict[str, object]:
    observed = datetime.now(UTC) - timedelta(seconds=1)
    return {
        "observation_id": OBSERVATION_ID,
        "agent_session_id": AGENT_SESSION_ID,
        "process_epoch": PROCESS_EPOCH,
        "auth_mode": "interactive_login",
        "agent_version": "2.1.42",
        "adapter_version": "runa.agent-auth.v1",
        "evidence_class": "provider_cli_login_status",
        "observed_at": _iso(observed),
        "valid_until": _iso(observed + timedelta(seconds=20)),
        "state": "authenticated",
        **overrides,
    }


@pytest.mark.contract
def test_agent_session_auth_decoder_accepts_exact_fresh_semantic_model() -> None:
    decoded = decode_for_operation("agentSessions.agentAuth", auth_payload())
    assert decoded.agent_session_id == AGENT_SESSION_ID
    assert decoded.evidence_class is AgentSessionAuthEvidenceClass.PROVIDER_CLI_LOGIN_STATUS
    assert decoded.state is AgentSessionAuthState.AUTHENTICATED


@pytest.mark.contract
@pytest.mark.parametrize(
    "overrides",
    (
        {"secret": "must-not-cross"},
        {"adapter_version": "runa.agent-auth.v2"},
        {"auth_mode": "interactive_login", "evidence_class": "credential_binding_authority"},
        {"auth_mode": "credential_binding", "state": "authenticated"},
        {"agent_version": "latest"},
        {"agent_session_id": "not-a-uuid"},
    ),
)
def test_agent_session_auth_decoder_fails_closed(overrides: dict[str, object]) -> None:
    with pytest.raises(DecodeFailure):
        decode_for_operation("agentSessions.agentAuth", auth_payload(**overrides))


@pytest.mark.contract
def test_agent_session_auth_decoder_rejects_stale_future_and_overlong_evidence() -> None:
    now = datetime.now(UTC)
    cases = (
        auth_payload(
            observed_at=_iso(now - timedelta(seconds=40)),
            valid_until=_iso(now - timedelta(seconds=10)),
        ),
        auth_payload(
            observed_at=_iso(now + timedelta(seconds=6)),
            valid_until=_iso(now + timedelta(seconds=20)),
        ),
        auth_payload(
            observed_at=_iso(now - timedelta(seconds=1)),
            valid_until=_iso(now + timedelta(seconds=31)),
        ),
    )
    for item in cases:
        with pytest.raises(DecodeFailure):
            decode_for_operation("agentSessions.agentAuth", item)


@pytest.mark.contract
def test_agent_session_auth_decoder_accepts_explicit_unavailable_negative_evidence() -> None:
    observed = datetime.now(UTC) - timedelta(seconds=1)
    decoded = decode_for_operation(
        "agentSessions.agentAuth",
        auth_payload(
            evidence_class="insufficient",
            state="unavailable",
            observed_at=_iso(observed),
            valid_until=_iso(observed),
        ),
    )
    assert decoded.state is AgentSessionAuthState.UNAVAILABLE


def _sync_response(request: PreparedRequest, _context: RequestContext) -> RawResponse:
    if request.operation_key == "agentSessions.get":
        return json_response(200, agent_session_payload())
    assert request.operation_key == "agentSessions.agentAuth"
    return json_response(200, auth_payload(), headers={"Cache-Control": "no-store"})


@pytest.mark.hermetic
def test_sync_manager_reads_auth_at_exact_agent_session_scope() -> None:
    recorder = SyncRecorder(_sync_response)
    client = Cuna(api_key="runa_sk_synthetic", transport=recorder)
    session = client.agent_sessions.get(AGENT_SESSION_ID)
    observation = client.agent_sessions.agent_auth(session)
    request = recorder.calls[-1][0]
    assert (request.method, request.relative_path, request.body) == (
        "GET",
        f"/v1/agent-sessions/{AGENT_SESSION_ID}/agent-auth",
        None,
    )
    assert observation.process_epoch == session.process_epoch


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_manager_reads_auth_at_exact_agent_session_scope() -> None:
    recorder = AsyncRecorder(_sync_response)
    client = AsyncCuna._with_transport(api_key="runa_sk_synthetic", transport=recorder)
    session = await client.agent_sessions.get(AGENT_SESSION_ID)
    observation = await client.agent_sessions.agent_auth(session)
    assert observation.agent_session_id == session.id
    await client.close()


@pytest.mark.asyncio
@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("overrides", "headers"),
    (
        ({"agent_session_id": SIBLING_ID}, {"Cache-Control": "no-store"}),
        ({"process_epoch": SIBLING_ID}, {"Cache-Control": "no-store"}),
        (
            {
                "auth_mode": "credential_binding",
                "evidence_class": "credential_binding_authority",
                "state": "configured",
            },
            {"Cache-Control": "no-store"},
        ),
        ({}, {}),
    ),
)
async def test_async_manager_rejects_mismatched_or_cacheable_evidence(
    overrides: dict[str, object], headers: dict[str, str]
) -> None:
    def responder(request: PreparedRequest, _context: RequestContext) -> RawResponse:
        if request.operation_key == "agentSessions.get":
            return json_response(200, agent_session_payload())
        return json_response(200, auth_payload(**overrides), headers=headers)

    recorder = AsyncRecorder(responder)
    client = AsyncCuna._with_transport(api_key="runa_sk_synthetic", transport=recorder)
    session = await client.agent_sessions.get(AGENT_SESSION_ID)
    with pytest.raises(ApiError) as malformed:
        await client.agent_sessions.agent_auth(session)
    assert malformed.value.code == "malformed_response"
    await client.close()

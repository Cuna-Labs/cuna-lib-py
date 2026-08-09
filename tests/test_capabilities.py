from __future__ import annotations

from copy import deepcopy

import pytest

from runa import (
    AsyncRuna,
    CapabilityAvailability,
    CapabilityMutationClass,
    CapabilityScope,
    Runa,
)
from runa._internal.contract import decode_for_operation
from runa._internal.contract.bridge import DecodeFailure
from runa.errors import ApiError, ConfigError

from .support import (
    SESSION_ID,
    AsyncRecorder,
    SyncRecorder,
    capability_snapshot_payload,
    json_response,
)


def capability_response(value: dict[str, object], status: int = 200):
    headers = {"etag": f'"{value["etag"]}"'} if status == 200 else None
    return json_response(status, value, headers=headers)


@pytest.mark.contract
def test_capability_decoder_is_typed_closed_and_secret_free() -> None:
    decoded = decode_for_operation("capabilities.get", capability_snapshot_payload())
    assert decoded.subject_scope is CapabilityScope.ACCOUNT
    assert decoded.capabilities[0].availability is CapabilityAvailability.UNSUPPORTED
    assert decoded.capabilities[0].mutation_class is CapabilityMutationClass.REVERSIBLE
    assert decoded.capabilities[0].reason_code == "agent_session_foundation_not_available"

    mutations = []
    for path, value in (
        (("subject_scope",), "agent_session"),
        (("expires_at",), "2026-08-08T11:59:59.000Z"),
        (("capabilities", 0, "availability"), "future"),
        (("capabilities", 0, "provider"), "internal"),
    ):
        payload = deepcopy(capability_snapshot_payload())
        target = payload
        for part in path[:-1]:
            target = target[part]  # type: ignore[index,assignment]
        target[path[-1]] = value  # type: ignore[index]
        mutations.append(payload)
    for payload in mutations:
        with pytest.raises(DecodeFailure):
            decode_for_operation("capabilities.get", payload)


@pytest.mark.hermetic
def test_sync_capabilities_get_uses_exact_query_and_subject_binding() -> None:
    value = capability_snapshot_payload()
    recorder = SyncRecorder(lambda _request, _context: capability_response(value))
    client = Runa(api_key="runa_sk_test", transport=recorder)
    assert client.capabilities is client.capabilities
    snapshot = client.capabilities.get(CapabilityScope.ACCOUNT)
    assert snapshot.etag == "a" * 64
    assert recorder.calls[0][0].relative_path == "/v1/capabilities?scope=account"

    machine = capability_snapshot_payload(subject_scope="machine", subject_id=SESSION_ID)
    recorder.responder = lambda _request, _context: capability_response(machine)
    snapshot = client.capabilities.get(CapabilityScope.MACHINE, SESSION_ID)
    assert snapshot.subject_id == SESSION_ID
    assert recorder.calls[1][0].relative_path == (
        f"/v1/capabilities?scope=machine&resource_id={SESSION_ID}"
    )
    client.close()


@pytest.mark.hermetic
@pytest.mark.asyncio
async def test_async_capabilities_get_matches_sync_wire_behavior() -> None:
    value = capability_snapshot_payload()
    recorder = AsyncRecorder(lambda _request, _context: capability_response(value))
    client = AsyncRuna._with_transport(api_key="runa_sk_test", transport=recorder)
    assert client.capabilities is client.capabilities
    snapshot = await client.capabilities.get(CapabilityScope.ACCOUNT)
    assert snapshot.subject_scope is CapabilityScope.ACCOUNT
    assert recorder.calls[0][0].relative_path == "/v1/capabilities?scope=account"
    await client.close()


@pytest.mark.hermetic
def test_agent_session_remains_an_explicit_unsupported_api_outcome() -> None:
    def unsupported(_request, _context):
        return json_response(
            501,
            {
                "type": "https://api.runacode.io/problems/capability_scope_not_available",
                "title": "Capability scope not available",
                "status": 501,
                "code": "capability_scope_not_available",
                "request_id": SESSION_ID,
                "retryable": False,
            },
        )

    recorder = SyncRecorder(unsupported)
    client = Runa(api_key="runa_sk_test", transport=recorder)
    with pytest.raises(ApiError) as error:
        client.capabilities.get(CapabilityScope.AGENT_SESSION, SESSION_ID)
    assert (error.value.status, error.value.code) == (501, "api_error")
    assert "scope=agent_session" in recorder.calls[0][0].relative_path
    client.close()


@pytest.mark.hermetic
def test_capability_request_and_etag_validation_fail_closed_before_leakage() -> None:
    calls = 0

    def mismatch(_request, _context):
        nonlocal calls
        calls += 1
        return json_response(
            200,
            capability_snapshot_payload(),
            headers={"etag": f'"{"b" * 64}"'},
        )

    client = Runa(api_key="runa_sk_test", transport=SyncRecorder(mismatch))
    with pytest.raises(ApiError) as error:
        client.capabilities.get(CapabilityScope.ACCOUNT)
    assert error.value.code == "malformed_response"
    for scope, resource_id in (
        (CapabilityScope.ACCOUNT, SESSION_ID),
        (CapabilityScope.MACHINE, None),
        (CapabilityScope.MACHINE, "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"),
        ("future", None),
    ):
        with pytest.raises(ConfigError):
            client.capabilities.get(scope, resource_id)  # type: ignore[arg-type]
    assert calls == 1
    client.close()

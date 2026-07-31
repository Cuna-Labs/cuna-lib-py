from __future__ import annotations

from types import MappingProxyType

import pytest

from runa._internal.contract import OPERATIONS, decode_for_operation, encode_for_operation
from runa._internal.contract.bridge import DecodeFailure, sanitize_response
from runa._internal.transport import (
    MAX_RESPONSE_BYTES,
    RawResponse,
    RequestContext,
    disposition,
    prepare_request,
)
from runa.errors import ApiError
from runa.models import SessionSnapshot

from .support import SESSION_ID, session_payload


@pytest.mark.contract
def test_registry_is_exactly_canonical_13() -> None:
    assert tuple(OPERATIONS) == (
        "me.get",
        "records.list",
        "sessions.checkpoint",
        "sessions.create",
        "sessions.delete",
        "sessions.exec",
        "sessions.get",
        "sessions.list",
        "sessions.open",
        "sessions.pause",
        "sessions.resume",
        "sessions.start",
        "sessions.stop",
    )
    assert OPERATIONS["sessions.create"].success_status == 201
    assert all(
        operation.success_status == 200
        for key, operation in OPERATIONS.items()
        if key != "sessions.create"
    )


@pytest.mark.contract
def test_encoder_omits_absent_and_preserves_supplied_none() -> None:
    value = encode_for_operation("sessions.create", {"name": "x", "agent": None})
    assert value == {"name": "x", "agent": None}
    assert "vcpus" not in value


@pytest.mark.contract
def test_decoder_preserves_only_detail_and_rejects_schema_additions() -> None:
    detail = {"nested": [1, {"x": None}]}
    record = {
        "id": SESSION_ID,
        "session_id": SESSION_ID,
        "kind": "kind",
        "summary": "summary",
        "detail": detail,
        "created_at": "2026-01-01T00:00:00Z",
        "new_field": object(),
    }
    with pytest.raises(DecodeFailure):
        decode_for_operation("records.list", [record])
    del record["new_field"]
    decoded = decode_for_operation("records.list", [record])
    assert decoded[0].detail is detail
    carrier = sanitize_response(
        record, ("id", "session_id", "kind", "summary", "detail", "created_at")
    )
    assert not carrier.unrecognized_fields  # type: ignore[union-attr]


@pytest.mark.contract
def test_all_statuses_and_agents_decode_exactly() -> None:
    for status in ("creating", "running", "paused", "suspended", "stopped", "deleted", "error"):
        for agent in ("claude-code", "codex", "openclaw", None):
            value = session_payload(status=status)
            if agent is None:
                del value["agent"]
            else:
                value["agent"] = agent
            decoded = decode_for_operation("sessions.get", value)
            assert isinstance(decoded, SessionSnapshot)
            assert decoded.status.value == status
            assert decoded.agent is None if agent is None else decoded.agent.value == agent


@pytest.mark.contract
@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("id"),
        lambda value: value.__setitem__("status", "future"),
        lambda value: value.__setitem__("agent", "future"),
        lambda value: value.__setitem__("url", 7),
        lambda value: value.__setitem__("user_id", "not-a-uuid"),
        lambda value: value.__setitem__("vcpus", True),
        lambda value: value.__setitem__("created_at", "not-a-date"),
        lambda value: value.__setitem__("extra", 1),
    ],
)
def test_malformed_known_session_shape_fails(mutation) -> None:
    value = session_payload()
    mutation(value)
    with pytest.raises(DecodeFailure):
        decode_for_operation("sessions.get", value)


@pytest.mark.contract
def test_me_usage_is_the_only_open_known_container() -> None:
    value = {
        "id": SESSION_ID,
        "email": "person@example.com",
        "workspace": {
            "assigned": True,
            "usage": {
                "est_spend_usd": 1,
                "est_remaining_usd": 2.5,
                "note": "estimate",
                "safe_future_member": {"opaque": True},
            },
        },
    }
    decoded = decode_for_operation("me.get", value)
    assert decoded.workspace.usage.estimated_remaining_usd == 2.5  # type: ignore[union-attr]
    value["workspace"]["safe_future_member"] = True  # type: ignore[index]
    with pytest.raises(DecodeFailure):
        decode_for_operation("me.get", value)


@pytest.mark.hermetic
def test_prepared_request_has_exact_body_and_protected_headers() -> None:
    request = prepare_request(
        operation_key="sessions.checkpoint",
        method="POST",
        origin="https://api.runacode.io",
        relative_path=f"/v1/sessions/{SESSION_ID}/checkpoint",
        api_key="runa_sk_value",
        body={"name": "café"},
        timeout_seconds=60,
    )
    assert request.body == {"name": "café"}
    assert request.body_bytes == b'{"name":"caf\xc3\xa9"}'
    assert dict(request.headers) == {
        "Authorization": "Bearer runa_sk_value",
        "User-Agent": "runa-sdk-python/0.1.0",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    }
    assert "request" not in {name.lower() for name in request.headers}

    bodyless = prepare_request(
        operation_key="sessions.list",
        method="GET",
        origin="https://api.runacode.io",
        relative_path="/v1/sessions",
        api_key="runa_sk_value",
        body=None,
        timeout_seconds=10,
    )
    assert bodyless.body is bodyless.body_bytes is None
    assert "Content-Type" not in bodyless.headers


@pytest.mark.hermetic
def test_request_context_is_private_and_shape_bound() -> None:
    context = RequestContext("sessions.list", "runa_req_" + "a" * 32, lambda: False)
    assert context.operation_key == "sessions.list"
    assert context.request_id == "runa_req_" + "a" * 32
    assert context.cancellation_requested() is False


@pytest.mark.hermetic
@pytest.mark.parametrize("success_status", [200, 201])
def test_disposition_status_precedes_media_and_body(
    success_status: int,
) -> None:
    headers = MappingProxyType({"content-type": "text/plain"})
    for status in ({200, 201, 202, 204} - {success_status}) | {300, 301, 307, 308}:
        with pytest.raises(ApiError) as malformed:
            disposition(RawResponse(status, headers, b"not json"), success_status)
        assert malformed.value.code == "malformed_response"
        assert malformed.value.status == status
    for status in (400, 401, 404, 409, 429, 500, 502, 503):
        with pytest.raises(ApiError) as api_error:
            disposition(RawResponse(status, headers, b"not json"), success_status)
        assert api_error.value.code == "api_error"
        assert api_error.value.status == status


@pytest.mark.hermetic
def test_disposition_is_exact_safe_and_bounded() -> None:
    good = RawResponse(
        200,
        MappingProxyType({"content-type": "application/json; charset=utf-8"}),
        b'{"ok":true}',
    )
    assert disposition(good, 200) == {"ok": True}
    with pytest.raises(ApiError) as wrong_media:
        disposition(RawResponse(200, {"content-type": "text/plain"}, b"{}"), 200)
    assert wrong_media.value.code == "malformed_response"
    with pytest.raises(ApiError):
        disposition(RawResponse(200, good.headers, b"\xff"), 200)
    with pytest.raises(ApiError):
        disposition(RawResponse(200, good.headers, b"x" * (MAX_RESPONSE_BYTES + 1)), 200)

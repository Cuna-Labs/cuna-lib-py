from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest

from cuna._internal.contract import OPERATIONS, decode_for_operation, encode_for_operation
from cuna._internal.contract.bridge import DecodeFailure, EncodeFailure, sanitize_response
from cuna._internal.transport import (
    MAX_RESPONSE_BYTES,
    RawResponse,
    RequestContext,
    disposition,
    prepare_request,
    security_dispatch_guard,
)
from cuna.errors import ApiError, ConfigError, ProblemAction, WorkspaceSyncProblem
from cuna.models import SessionSnapshot
from tools.contract_gate import CANONICAL_SNAPSHOT_SHA256, validate_snapshot

from .support import SESSION_ID, session_payload


@pytest.mark.contract
def test_registry_is_exactly_the_canonical_1_7_sdk_projection() -> None:
    assert tuple(OPERATIONS) == (
        "agentSessions.agentAuth",
        "agentSessions.create",
        "agentSessions.createTerminalConnection",
        "agentSessions.get",
        "agentSessions.list",
        "agentSessions.rename",
        "agentSessions.terminate",
        "capabilities.get",
        "machineCreates.get",
        "machineCreates.reconcile",
        "me.get",
        "records.list",
        "sessions.agentAuth",
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
        "workspaceBindings.create",
        "workspaceBindings.get",
        "workspaces.sync.begin",
        "workspaces.sync.changes",
        "workspaces.sync.chunk",
        "workspaces.sync.chunkDownload",
        "workspaces.sync.commit",
        "workspaces.sync.negotiate",
        "workspaces.sync.reconcile",
    )
    assert all(
        operation.source_reference == f"contracts/runa-sdk.projection.json#/operations/{key}"
        for key, operation in OPERATIONS.items()
    )
    assert OPERATIONS["sessions.create"].success_status == 201
    assert all(
        operation.success_status == 200
        for key, operation in OPERATIONS.items()
        if key
        not in {
            "sessions.create",
            "agentSessions.create",
            "agentSessions.createTerminalConnection",
        }
    )


@pytest.mark.contract
def test_generated_manifest_and_local_snapshot_digests_are_exact() -> None:
    generated = Path(__file__).parents[1] / "src/cuna/_internal/contract/generated"
    manifest = json.loads((generated / "generated-manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        assert hashlib.sha256((generated / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    contracts = Path(__file__).parents[1] / "contracts"
    snapshot = (contracts / "runa-sdk-contract.snapshot.json").read_bytes()
    provenance = json.loads(
        (contracts / "runa-sdk-contract.provenance.json").read_text(encoding="utf-8")
    )
    assert hashlib.sha256(snapshot).hexdigest() == CANONICAL_SNAPSHOT_SHA256
    assert provenance["artifacts"]["snapshot"]["sha256"] == CANONICAL_SNAPSHOT_SHA256
    assert provenance["status"] == "BLOCKED"
    assert provenance["approval_reference"] is None
    assert provenance["canonical_ref"] is None
    assert provenance["source_revision"] is None


@pytest.mark.contract
def test_generated_binding_is_exactly_openapi_1_7_projection_closure() -> None:
    root = Path(__file__).parents[1]
    projection_path = root / "contracts/runa-sdk.projection.json"
    projection_bytes = projection_path.read_bytes()
    projection = json.loads(projection_bytes)
    manifest = json.loads(
        (root / "src/cuna/_internal/contract/generated/generated-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert hashlib.sha256(projection_bytes).hexdigest() == (
        "693dec9fd0d00fb541b4238e47d8f6bbd5211e4f18dcd133ae60b58462b44089"
    )
    assert manifest["projection"] == {
        "path": "runa-sdk.projection.json",
        "sha256": "693dec9fd0d00fb541b4238e47d8f6bbd5211e4f18dcd133ae60b58462b44089",
        "version": "1.7.0",
    }
    assert projection["contractVersion"] == "1.7.0"
    assert projection["wire"]["requestAccept"] == ("application/json, application/problem+json")
    assert projection["wire"]["sdkOperationCount"] == 33
    assert tuple(sorted(projection["operations"])) == tuple(OPERATIONS)
    schemas = projection["schemas"]
    assert len(schemas) == 51
    referenced: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
                referenced.add(reference.rsplit("/", 1)[-1])
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(projection)
    assert len(referenced) == 47
    assert referenced <= set(schemas)


@pytest.mark.contract
def test_contract_gate_rejects_semantic_mutations() -> None:
    snapshot = json.loads(
        (Path(__file__).parents[1] / "contracts/runa-sdk-contract.snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_snapshot(snapshot) is None
    wire_mutation = json.loads(json.dumps(snapshot))
    wire_mutation["operations"][0]["http_binding"]["follow_redirects"] = True
    assert validate_snapshot(wire_mutation) == "operation-semantics-drift"
    removed = json.loads(json.dumps(snapshot))
    removed["operations"] = [
        item for item in removed["operations"] if item["operation_key"] != "sessions.create"
    ]
    assert validate_snapshot(removed) == "operation-set-drift"
    renamed = json.loads(json.dumps(snapshot))
    renamed["operations"][0]["unexpected"] = True
    assert validate_snapshot(renamed) == "operation-shape-invalid"


@pytest.mark.contract
def test_encoder_omits_absent_and_preserves_supplied_none() -> None:
    value = encode_for_operation("sessions.create", {"name": "x", "agent": None})
    assert value == {"name": "x", "agent": None}
    assert "vcpus" not in value
    with pytest.raises(EncodeFailure):
        encode_for_operation("sessions.create", {"name": "x", "extra": True})


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
def test_closed_containers_reject_protected_content_without_transforming_safe_detail() -> None:
    marker = bytes((114, 117, 110, 116, 105, 109, 101, 95, 105, 100)).decode()
    session = session_payload()
    session[marker] = "secret"
    with pytest.raises(DecodeFailure):
        decode_for_operation("sessions.get", session)
    detail = {marker: ["secret", {"nested": marker}]}
    record = {
        "id": SESSION_ID,
        "session_id": SESSION_ID,
        "kind": "kind",
        "summary": "summary",
        "detail": detail,
        "created_at": "2026-01-01T00:00:00Z",
    }
    with pytest.raises(DecodeFailure):
        decode_for_operation("records.list", [record])
    safe_detail = {"safe": ["value", {"nested": 1}]}
    record["detail"] = safe_detail
    decoded = decode_for_operation("records.list", [record])
    assert decoded[0].detail is safe_detail


@pytest.mark.contract
def test_session_name_accepts_public_network_vocabulary() -> None:
    session = session_payload()
    session["name"] = "e2e-egress-verification"
    decoded = decode_for_operation("sessions.get", session)
    assert decoded.name == "e2e-egress-verification"


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
            "id": "77777777-7777-4777-8777-777777777777",
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


@pytest.mark.contract
@pytest.mark.parametrize(
    ("operation", "value"),
    [
        ("sessions.list", {}),
        ("sessions.exec", {"exit_code": 0}),
        (
            "sessions.exec",
            {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration_ms": -1,
                "stdout_truncated": False,
                "stderr_truncated": False,
            },
        ),
        ("sessions.checkpoint", {"ok": False}),
        ("sessions.open", {"url": 7}),
        (
            "records.list",
            [
                {
                    "id": SESSION_ID,
                    "session_id": SESSION_ID,
                    "kind": "k",
                    "summary": "s",
                    "detail": None,
                    "created_at": "2026-99-99T00:00:00Z",
                }
            ],
        ),
        (
            "me.get",
            {"id": SESSION_ID, "email": "a@b", "workspace": None},
        ),
        (
            "me.get",
            {"id": SESSION_ID, "email": "a@b", "workspace": {"assigned": True, "usage": []}},
        ),
        (
            "me.get",
            {
                "id": SESSION_ID,
                "email": "a@b",
                "workspace": {"assigned": True, "usage": {"est_spend_usd": 1}},
            },
        ),
        (
            "me.get",
            {
                "id": SESSION_ID,
                "email": "a@b",
                "workspace": {
                    "assigned": True,
                    "usage": {
                        "est_spend_usd": float("inf"),
                        "est_remaining_usd": 1,
                        "note": "n",
                    },
                },
            },
        ),
        (
            "me.get",
            {
                "id": SESSION_ID,
                "email": "a@b",
                "workspace": {"assigned": False, "waitlist_position": True},
            },
        ),
    ],
)
def test_known_response_shape_edge_cases_fail(operation: str, value: object) -> None:
    with pytest.raises(DecodeFailure):
        decode_for_operation(operation, value)


@pytest.mark.contract
def test_decoder_unknown_operation_is_not_silently_accepted() -> None:
    with pytest.raises(KeyError):
        decode_for_operation("unknown.operation", {})


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
        "User-Agent": "cuna-sdk-python/0.1.0",
        "Accept": "application/json, application/problem+json",
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
    context = RequestContext("sessions.list", "cuna_req_" + "a" * 32, lambda: False)
    assert context.operation_key == "sessions.list"
    assert context.request_id == "cuna_req_" + "a" * 32
    assert context.cancellation_requested() is False


@pytest.mark.hermetic
def test_dispatch_guard_rejects_every_destination_or_descriptor_mutation() -> None:
    prepared = prepare_request(
        operation_key="sessions.list",
        method="GET",
        origin="https://api.runacode.io",
        relative_path="/v1/sessions",
        api_key="runa_sk_value",
        body=None,
        timeout_seconds=10,
    )
    request_context = RequestContext("sessions.list", "cuna_req_" + "a" * 32, lambda: False)
    expected = {
        "expected_origin": "https://api.runacode.io",
        "expected_operation_key": "sessions.list",
        "expected_method": "GET",
        "expected_path": "/v1/sessions",
    }
    security_dispatch_guard(prepared, request_context, **expected)

    mutations = (
        replace(prepared, origin="https://example.com"),
        replace(prepared, operation_key="me.get"),
        replace(prepared, method="POST"),
        replace(prepared, relative_path="/v1/me"),
    )
    for mutated in mutations:
        with pytest.raises(ConfigError):
            security_dispatch_guard(mutated, request_context, **expected)
    with pytest.raises(ConfigError):
        security_dispatch_guard(
            prepared,
            replace(request_context, operation_key="me.get"),
            **expected,
        )


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


@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "x" * 121),
        ("code", "a" * 65),
    ],
)
def test_problem_parser_enforces_openapi_string_bounds(field: str, value: str) -> None:
    problem = {
        "type": "https://api.runacode.io/problems/request_failed",
        "title": "Request failed",
        "status": 400,
        "code": "request_failed",
        "request_id": "00000000-0000-0000-0000-000000000000",
        "retryable": False,
    }
    problem[field] = value
    if field == "code":
        problem["type"] = f"https://api.runacode.io/problems/{value}"
    response = RawResponse(
        400,
        MappingProxyType({"content-type": "application/json"}),
        json.dumps(problem).encode(),
    )
    with pytest.raises(ApiError) as error:
        disposition(response, 200)
    assert error.value.problem is None


@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("selected_protocol", "capabilities"),
    [
        (None, []),
        (
            2,
            [
                "atomic_generation_commit",
                "bounded_manifest_pages",
                "content_digest_verification",
                "explicit_reconciliation",
                "ordered_generation_changes",
                "policy_bound_admission",
            ],
        ),
    ],
)
def test_workspace_sync_problem_preserves_exact_negotiation_evidence(
    selected_protocol: int | None, capabilities: list[str]
) -> None:
    body = {
        "type": "https://api.runacode.io/problems/workspace_sync_protocol_unavailable",
        "title": "Workspace sync protocol unavailable",
        "status": 426,
        "code": "workspace_sync_protocol_unavailable",
        "request_id": "00000000-0000-0000-0000-000000000000",
        "retryable": False,
        "action": "none",
        "selected_protocol": selected_protocol,
        "capabilities": capabilities,
        "detail": "The requested protocol range cannot be selected.",
    }
    with pytest.raises(ApiError) as error:
        disposition(
            RawResponse(
                426,
                MappingProxyType({"content-type": "application/problem+json; charset=utf-8"}),
                json.dumps(body).encode(),
            ),
            200,
        )
    problem = error.value.problem
    assert isinstance(problem, WorkspaceSyncProblem)
    assert problem.selected_protocol == selected_protocol
    assert problem.capabilities == tuple(capabilities)
    assert problem.action is ProblemAction.NONE


@pytest.mark.hermetic
@pytest.mark.parametrize(
    ("selected_protocol", "capabilities"),
    [
        (None, ["atomic_generation_commit"]),
        (2, []),
        (2, ["atomic_generation_commit"] * 6),
        ([2], []),
    ],
)
def test_workspace_sync_problem_rejects_noncanonical_capability_binding(
    selected_protocol: object, capabilities: list[str]
) -> None:
    body = {
        "type": "https://api.runacode.io/problems/workspace_sync_protocol_unavailable",
        "title": "Workspace sync protocol unavailable",
        "status": 426,
        "code": "workspace_sync_protocol_unavailable",
        "request_id": "00000000-0000-0000-0000-000000000000",
        "retryable": False,
        "action": "none",
        "selected_protocol": selected_protocol,
        "capabilities": capabilities,
        "detail": "The requested protocol range cannot be selected.",
    }
    with pytest.raises(ApiError) as error:
        disposition(
            RawResponse(
                426,
                MappingProxyType({"content-type": "application/problem+json"}),
                json.dumps(body).encode(),
            ),
            200,
        )
    assert error.value.problem is None

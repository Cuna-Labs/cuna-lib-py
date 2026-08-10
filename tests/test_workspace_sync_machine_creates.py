from __future__ import annotations

import base64

import pytest

from cuna import (
    AsyncCuna,
    Cuna,
    WorkspaceBindingCreateRequest,
    WorkspaceBindingLookup,
    WorkspaceSyncBeginRequest,
    WorkspaceSyncChangeOptions,
    WorkspaceSyncChangePage,
    WorkspaceSyncChunkReceipt,
    WorkspaceSyncChunkRef,
    WorkspaceSyncCommitReceipt,
    WorkspaceSyncCommitRequest,
    WorkspaceSyncManifestEntry,
    WorkspaceSyncManifestPageRequest,
    WorkspaceSyncManifestReceipt,
    WorkspaceSyncProtocolRange,
    WorkspaceSyncReconcileReceipt,
    WorkspaceSyncReconcileRequest,
    WorkspaceSyncSession,
)
from cuna._internal.transport import PreparedRequest
from cuna.errors import ApiError, ConfigError

from .support import AsyncRecorder, SyncRecorder, json_response

WORKSPACE_ID = "77777777-7777-4777-8777-777777777777"
WORKSPACE_BINDING_ID = "88888888-8888-4888-8888-888888888888"
PROJECT_ID = "22222222-2222-4222-8222-222222222222"
LOCAL_INSTANCE_ID = "33333333-3333-4333-8333-333333333333"
MACHINE_ID = "11111111-1111-4111-8111-111111111111"
SYNC_ID = "99999999-9999-4999-8999-999999999999"
REQUEST_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
POLICY_DIGEST = "a" * 64
MANIFEST_ROOT = "b" * 64
CHUNK_DIGEST = "c" * 64
DOWNLOAD_BYTES = b"payload"
DOWNLOAD_DIGEST = "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5"
CAPABILITIES = [
    "atomic_generation_commit",
    "bounded_manifest_pages",
    "content_digest_verification",
    "explicit_reconciliation",
    "ordered_generation_changes",
    "policy_bound_admission",
]


def sync_session_payload(**overrides: object) -> dict[str, object]:
    return {
        "id": SYNC_ID,
        "workspace_id": WORKSPACE_ID,
        "machine_id": MACHINE_ID,
        "base_generation": 4,
        "exclusion_policy_digest": POLICY_DIGEST,
        "selected_protocol": 2,
        "capabilities": CAPABILITIES,
        "state": "staging",
        "manifest_entry_count": 1,
        "manifest_encoded_bytes": 128,
        "content_bytes": 7,
        "expires_at": "2026-08-09T12:10:00Z",
        "created_at": "2026-08-09T12:00:00Z",
        "updated_at": "2026-08-09T12:00:01Z",
        **overrides,
    }


def workspace_data(operation: str) -> dict[str, object]:
    if operation == "workspaces.sync.begin":
        return sync_session_payload()
    if operation == "workspaces.sync.negotiate":
        return {
            "sync": sync_session_payload(last_page_index=0),
            "page_index": 0,
            "page_digest": "d" * 64,
            "missing_digests": [CHUNK_DIGEST],
        }
    if operation == "workspaces.sync.chunk":
        return {
            "selected_protocol": 2,
            "digest": CHUNK_DIGEST,
            "byte_length": 7,
            "stored": True,
        }
    if operation == "workspaces.sync.chunkDownload":
        return {
            "selected_protocol": 2,
            "digest": DOWNLOAD_DIGEST,
            "byte_length": len(DOWNLOAD_BYTES),
            "minimum_reader": 1,
            "content_base64": base64.b64encode(DOWNLOAD_BYTES).decode("ascii"),
        }
    if operation == "workspaces.sync.commit":
        return {
            "selected_protocol": 2,
            "state": "committed",
            "generation": 5,
            "manifest_root": MANIFEST_ROOT,
            "committed_at": "2026-08-09T12:00:02Z",
            "minimum_reader": 1,
            "minimum_writer": 2,
        }
    if operation == "workspaces.sync.changes":
        return {"selected_protocol": 2, "items": [], "next_cursor": None}
    return {
        "selected_protocol": 2,
        "status": "converged",
        "active_generation": 5,
        "active_manifest_root": MANIFEST_ROOT,
        "exclusion_policy_digest": POLICY_DIGEST,
    }


def workspace_envelope(
    operation: str = "workspaces.sync.changes", **overrides: object
) -> dict[str, object]:
    return {
        "request_id": REQUEST_ID,
        "selected_protocol": 2,
        "capabilities": CAPABILITIES,
        "data": workspace_data(operation),
        **overrides,
    }


def workspace_binding_payload(**overrides: object) -> dict[str, object]:
    return {
        "binding_id": WORKSPACE_BINDING_ID,
        "workspace_id": WORKSPACE_ID,
        "project_id": PROJECT_ID,
        "local_instance_id": LOCAL_INSTANCE_ID,
        "machine_id": MACHINE_ID,
        "remote_root": f"/workspace/projects/{PROJECT_ID}",
        "exclusion_policy_digest": POLICY_DIGEST,
        "active_generation": 0,
        "active_manifest_root": "0" * 64,
        "binding_epoch": 1,
        "minimum_reader": 1,
        "minimum_writer": 1,
        "created_at": "2026-08-09T12:00:00Z",
        "updated_at": "2026-08-09T12:00:00Z",
        **overrides,
    }


def machine_create_payload(**overrides: object) -> dict[str, object]:
    return {
        "id": REQUEST_ID,
        "machine_id": MACHINE_ID,
        "state": "in_progress",
        "retryable": True,
        "action": "wait",
        "updated_at": "2026-08-09T12:00:00Z",
        **overrides,
    }


def responder(request: PreparedRequest, _context: object):
    if request.operation_key.startswith("workspaceBindings."):
        return json_response(200, workspace_binding_payload())
    if request.operation_key.startswith("machineCreates."):
        return json_response(200, machine_create_payload())
    return json_response(200, workspace_envelope(request.operation_key))


def sync_requests(client: Cuna) -> None:
    protocol = WorkspaceSyncProtocolRange(minimum=1, maximum=2)
    begin = client.workspace_sync.begin(
        WORKSPACE_ID,
        WorkspaceSyncBeginRequest(
            workspace_binding_id=WORKSPACE_BINDING_ID,
            machine_id=MACHINE_ID,
            base_generation=4,
            exclusion_policy_digest=POLICY_DIGEST,
            protocol=protocol,
            minimum_reader=1,
            minimum_writer=2,
        ),
        "workspace-begin-1",
    )
    negotiated = client.workspace_sync.negotiate(
        SYNC_ID,
        WorkspaceSyncManifestPageRequest(
            page_index=0,
            is_last=True,
            minimum_reader=1,
            minimum_writer=2,
            entries=[
                WorkspaceSyncManifestEntry(
                    path="src/main.py",
                    kind="file",
                    byte_length=7,
                    executable=False,
                    chunks=[WorkspaceSyncChunkRef(CHUNK_DIGEST, 7)],
                    link_target=None,
                )
            ],
        ),
        "workspace-manifest-1",
    )
    uploaded = client.workspace_sync.upload_chunk(
        SYNC_ID, CHUNK_DIGEST, b"payload", "workspace-chunk-1"
    )
    downloaded = client.workspace_sync.download_chunk(SYNC_ID, DOWNLOAD_DIGEST)
    committed = client.workspace_sync.commit(
        SYNC_ID,
        WorkspaceSyncCommitRequest(
            expected_generation=4,
            exclusion_policy_digest=POLICY_DIGEST,
            manifest_root=MANIFEST_ROOT,
            minimum_reader=1,
            minimum_writer=2,
        ),
        "workspace-commit-1",
    )
    changes = client.workspace_sync.changes(
        SYNC_ID, WorkspaceSyncChangeOptions(reader_version=2, cursor="opaque", limit=25)
    )
    reconciled = client.workspace_sync.reconcile(
        WORKSPACE_ID,
        WorkspaceSyncReconcileRequest(
            workspace_binding_id=WORKSPACE_BINDING_ID,
            machine_id=MACHINE_ID,
            observed_generation=4,
            exclusion_policy_digest=POLICY_DIGEST,
            manifest_root=MANIFEST_ROOT,
            protocol=protocol,
        ),
        "workspace-reconcile-1",
    )
    machine_get = client.machine_creates.get(REQUEST_ID)
    machine_reconcile = client.machine_creates.reconcile(REQUEST_ID)

    for envelope in (begin, negotiated, uploaded, committed, changes, reconciled):
        assert envelope.request_id == REQUEST_ID
        assert envelope.selected_protocol == 2
        assert envelope.capabilities == tuple(CAPABILITIES)
    assert isinstance(begin.data, WorkspaceSyncSession)
    assert isinstance(negotiated.data, WorkspaceSyncManifestReceipt)
    assert isinstance(uploaded.data, WorkspaceSyncChunkReceipt)
    assert downloaded == DOWNLOAD_BYTES
    assert isinstance(committed.data, WorkspaceSyncCommitReceipt)
    assert isinstance(changes.data, WorkspaceSyncChangePage)
    assert isinstance(reconciled.data, WorkspaceSyncReconcileReceipt)
    assert machine_get.id == REQUEST_ID
    assert machine_reconcile.machine_id == MACHINE_ID


@pytest.mark.hermetic
@pytest.mark.contract
def test_workspace_sync_and_machine_create_sync_wire_contract() -> None:
    recorder = SyncRecorder(responder)
    client = Cuna(api_key="runa_sk_test", transport=recorder)
    sync_requests(client)

    requests = [call[0] for call in recorder.calls]
    assert [request.operation_key for request in requests] == [
        "workspaces.sync.begin",
        "workspaces.sync.negotiate",
        "workspaces.sync.chunk",
        "workspaces.sync.chunkDownload",
        "workspaces.sync.commit",
        "workspaces.sync.changes",
        "workspaces.sync.reconcile",
        "machineCreates.get",
        "machineCreates.reconcile",
    ]
    assert requests[0].relative_path == f"/v1/workspaces/{WORKSPACE_ID}/sync-sessions"
    assert requests[0].headers["Idempotency-Key"] == "workspace-begin-1"
    assert dict(requests[0].body or {}) == {
        "workspace_binding_id": WORKSPACE_BINDING_ID,
        "machine_id": MACHINE_ID,
        "base_generation": 4,
        "exclusion_policy_digest": POLICY_DIGEST,
        "protocol": {"minimum": 1, "maximum": 2},
        "minimum_reader": 1,
        "minimum_writer": 2,
    }
    assert requests[2].body is None
    assert requests[2].body_bytes == b"payload"
    assert requests[2].headers["Content-Type"] == "application/octet-stream"
    assert requests[3].relative_path == (f"/v1/workspace-sync/{SYNC_ID}/chunks/{DOWNLOAD_DIGEST}")
    assert requests[5].relative_path == (
        f"/v1/workspace-sync/{SYNC_ID}/changes?reader_version=2&cursor=opaque&limit=25"
    )
    assert requests[8].relative_path == f"/v1/machine-creates/{REQUEST_ID}/reconcile"
    client.close()


@pytest.mark.hermetic
@pytest.mark.contract
def test_workspace_binding_create_and_exact_lookup_wire_contract() -> None:
    recorder = SyncRecorder(responder)
    client = Cuna(api_key="runa_sk_test", transport=recorder)
    created = client.workspace_bindings.create(
        WorkspaceBindingCreateRequest(
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            local_instance_id=LOCAL_INSTANCE_ID,
            machine_id=MACHINE_ID,
            exclusion_policy_digest=POLICY_DIGEST,
            excluded_prefixes=[".git", "node_modules"],
        ),
        "binding-create-1",
    )
    fetched = client.workspace_bindings.get(
        WORKSPACE_BINDING_ID,
        WorkspaceBindingLookup(
            workspace_id=WORKSPACE_ID,
            project_id=PROJECT_ID,
            local_instance_id=LOCAL_INSTANCE_ID,
            machine_id=MACHINE_ID,
            exclusion_policy_digest=POLICY_DIGEST,
        ),
    )

    assert created == fetched
    assert created.binding_id == WORKSPACE_BINDING_ID
    create_request, get_request = (call[0] for call in recorder.calls)
    assert create_request.relative_path == "/v1/workspace-bindings"
    assert create_request.headers["Idempotency-Key"] == "binding-create-1"
    assert dict(create_request.body or {}) == {
        "workspace_id": WORKSPACE_ID,
        "project_id": PROJECT_ID,
        "local_instance_id": LOCAL_INSTANCE_ID,
        "machine_id": MACHINE_ID,
        "exclusion_policy_digest": POLICY_DIGEST,
        "excluded_prefixes": [".git", "node_modules"],
    }
    assert get_request.relative_path == (
        f"/v1/workspace-bindings/{WORKSPACE_BINDING_ID}"
        f"?workspace_id={WORKSPACE_ID}&project_id={PROJECT_ID}"
        f"&local_instance_id={LOCAL_INSTANCE_ID}&machine_id={MACHINE_ID}"
        f"&exclusion_policy_digest={POLICY_DIGEST}"
    )
    client.close()


@pytest.mark.hermetic
@pytest.mark.contract
@pytest.mark.asyncio
async def test_workspace_sync_and_machine_create_async_wire_contract() -> None:
    recorder = AsyncRecorder(responder)
    client = AsyncCuna._with_transport(api_key="runa_sk_test", transport=recorder)
    protocol = WorkspaceSyncProtocolRange(minimum=1, maximum=2)

    await client.workspace_sync.begin(
        WORKSPACE_ID,
        WorkspaceSyncBeginRequest(
            workspace_binding_id=WORKSPACE_BINDING_ID,
            machine_id=MACHINE_ID,
            base_generation=0,
            exclusion_policy_digest=POLICY_DIGEST,
            protocol=protocol,
            minimum_reader=1,
            minimum_writer=1,
        ),
        "workspace-begin-2",
    )
    await client.workspace_sync.negotiate(
        SYNC_ID,
        WorkspaceSyncManifestPageRequest(0, True, 1, 1, []),
        "workspace-manifest-2",
    )
    await client.workspace_sync.upload_chunk(SYNC_ID, CHUNK_DIGEST, b"async", "workspace-chunk-2")
    assert await client.workspace_sync.download_chunk(SYNC_ID, DOWNLOAD_DIGEST) == DOWNLOAD_BYTES
    await client.workspace_sync.commit(
        SYNC_ID,
        WorkspaceSyncCommitRequest(0, POLICY_DIGEST, MANIFEST_ROOT, 1, 1),
        "workspace-commit-2",
    )
    await client.workspace_sync.changes(SYNC_ID, WorkspaceSyncChangeOptions(1))
    await client.workspace_sync.reconcile(
        WORKSPACE_ID,
        WorkspaceSyncReconcileRequest(
            WORKSPACE_BINDING_ID, MACHINE_ID, 0, POLICY_DIGEST, MANIFEST_ROOT, protocol
        ),
        "workspace-reconcile-2",
    )
    await client.machine_creates.get(REQUEST_ID)
    await client.machine_creates.reconcile(REQUEST_ID)
    binding_request = WorkspaceBindingCreateRequest(
        WORKSPACE_ID,
        PROJECT_ID,
        LOCAL_INSTANCE_ID,
        MACHINE_ID,
        POLICY_DIGEST,
        [],
    )
    await client.workspace_bindings.create(binding_request, "binding-create-2")
    await client.workspace_bindings.get(
        WORKSPACE_BINDING_ID,
        WorkspaceBindingLookup(
            WORKSPACE_ID, PROJECT_ID, LOCAL_INSTANCE_ID, MACHINE_ID, POLICY_DIGEST
        ),
    )

    assert len(recorder.calls) == 11
    assert recorder.calls[2][0].body_bytes == b"async"
    assert recorder.calls[5][0].relative_path.endswith("?reader_version=1")
    assert recorder.calls[9][0].operation_key == "workspaceBindings.create"
    await client.close()


@pytest.mark.hermetic
@pytest.mark.contract
def test_workspace_sync_invalid_inputs_fail_before_transport() -> None:
    recorder = SyncRecorder(responder)
    client = Cuna(api_key="runa_sk_test", transport=recorder)

    with pytest.raises(ConfigError):
        client.workspace_sync.changes(SYNC_ID, WorkspaceSyncChangeOptions(reader_version=0))
    with pytest.raises(ConfigError):
        client.workspace_sync.changes(
            SYNC_ID, WorkspaceSyncChangeOptions(reader_version=1, cursor="")
        )
    with pytest.raises(ConfigError):
        client.workspace_sync.changes(
            SYNC_ID, WorkspaceSyncChangeOptions(reader_version=1, limit=1001)
        )
    with pytest.raises(ConfigError):
        client.workspace_sync.upload_chunk(SYNC_ID, "not-a-digest", b"data", "valid-key-1")
    with pytest.raises(ConfigError):
        client.workspace_sync.download_chunk(SYNC_ID, "not-a-digest")
    with pytest.raises(ConfigError):
        client.workspace_sync.upload_chunk(
            SYNC_ID,
            CHUNK_DIGEST,
            "not-bytes",
            "valid-key-2",  # type: ignore[arg-type]
        )
    with pytest.raises(ConfigError):
        client.workspace_sync.begin(
            WORKSPACE_ID,
            WorkspaceSyncBeginRequest(
                WORKSPACE_ID,
                MACHINE_ID,
                0,
                POLICY_DIGEST,
                WorkspaceSyncProtocolRange(1, 2),
                1,
                1,
            ),
            "valid-key-4",
        )
    with pytest.raises(ConfigError):
        client.workspace_bindings.create(
            WorkspaceBindingCreateRequest(
                WORKSPACE_ID,
                PROJECT_ID,
                LOCAL_INSTANCE_ID,
                MACHINE_ID,
                POLICY_DIGEST,
                ["../secret"],
            ),
            "binding-key-1",
        )
    with pytest.raises(ConfigError):
        client.workspace_sync.begin(
            "not-a-uuid",
            WorkspaceSyncBeginRequest(
                WORKSPACE_BINDING_ID,
                MACHINE_ID,
                0,
                POLICY_DIGEST,
                WorkspaceSyncProtocolRange(1, 2),
                1,
                1,
            ),
            "valid-key-3",
        )
    with pytest.raises(ConfigError):
        client.workspace_sync.begin(
            WORKSPACE_ID,
            WorkspaceSyncBeginRequest(
                WORKSPACE_BINDING_ID,
                MACHINE_ID,
                0,
                POLICY_DIGEST,
                WorkspaceSyncProtocolRange(1, 2),
                1,
                1,
            ),
            "short",
        )
    assert recorder.calls == []
    client.close()


@pytest.mark.hermetic
@pytest.mark.contract
@pytest.mark.parametrize(
    "data",
    [
        {
            "selected_protocol": 2,
            "digest": CHUNK_DIGEST,
            "byte_length": len(DOWNLOAD_BYTES),
            "minimum_reader": 1,
            "content_base64": base64.b64encode(DOWNLOAD_BYTES).decode("ascii"),
        },
        {
            "selected_protocol": 2,
            "digest": DOWNLOAD_DIGEST,
            "byte_length": len(DOWNLOAD_BYTES),
            "minimum_reader": 1,
            "content_base64": base64.b64encode(b"tampered").decode("ascii"),
        },
        {
            "selected_protocol": 2,
            "digest": DOWNLOAD_DIGEST,
            "byte_length": len(DOWNLOAD_BYTES),
            "minimum_reader": 1,
            "content_base64": "cGF5bG9hZA===",
        },
    ],
)
def test_workspace_chunk_download_rejects_untrusted_content(data: dict[str, object]) -> None:
    response = workspace_envelope("workspaces.sync.chunkDownload")
    response["data"] = data
    client = Cuna(
        api_key="runa_sk_test",
        transport=SyncRecorder(lambda _request, _context: json_response(200, response)),
    )
    with pytest.raises(ApiError) as error:
        client.workspace_sync.download_chunk(SYNC_ID, DOWNLOAD_DIGEST)
    assert error.value.code == "malformed_response"
    client.close()


@pytest.mark.hermetic
@pytest.mark.contract
@pytest.mark.parametrize(
    "value",
    [
        workspace_envelope(extra=True),
        workspace_envelope(request_id="not-a-uuid"),
        workspace_envelope(selected_protocol=3),
        workspace_envelope(capabilities=["unknown"]),
        workspace_envelope(data=[]),
    ],
)
def test_workspace_sync_malformed_envelopes_fail_closed(value: dict[str, object]) -> None:
    client = Cuna(
        api_key="runa_sk_test",
        transport=SyncRecorder(lambda _request, _context: json_response(200, value)),
    )
    with pytest.raises(ApiError) as error:
        client.workspace_sync.changes(SYNC_ID, WorkspaceSyncChangeOptions(1))
    assert error.value.code == "malformed_response"
    client.close()


@pytest.mark.hermetic
@pytest.mark.contract
@pytest.mark.parametrize(
    "value",
    [
        machine_create_payload(extra=True),
        machine_create_payload(id="not-a-uuid"),
        machine_create_payload(state="future"),
        machine_create_payload(retryable=1),
        machine_create_payload(action="future"),
        machine_create_payload(updated_at="not-a-date"),
    ],
)
def test_machine_create_malformed_responses_fail_closed(value: dict[str, object]) -> None:
    client = Cuna(
        api_key="runa_sk_test",
        transport=SyncRecorder(lambda _request, _context: json_response(200, value)),
    )
    with pytest.raises(ApiError) as error:
        client.machine_creates.get(REQUEST_ID)
    assert error.value.code == "malformed_response"
    client.close()

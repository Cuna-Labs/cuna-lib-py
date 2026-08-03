from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import runa.client as client_module
from runa import (
    AsyncRuna,
    ExecOptions,
    OutboundPolicy,
    OutboundPolicyMode,
    Runa,
    SessionAgent,
    SessionCreateOptions,
    SessionStatus,
)
from runa._internal.transport import PreparedRequest, RawResponse, RequestContext
from runa.errors import ApiError, ConfigError

from .support import (
    SECOND_SESSION_ID,
    SESSION_ID,
    AsyncRecorder,
    SyncRecorder,
    json_response,
    session_payload,
)


def operation_response(request: PreparedRequest, _context: RequestContext) -> RawResponse:
    key = request.operation_key
    if key == "sessions.create":
        return json_response(201, session_payload())
    if key == "sessions.list":
        return json_response(200, [session_payload(), session_payload(SECOND_SESSION_ID)])
    if key in {
        "sessions.get",
        "sessions.start",
        "sessions.pause",
        "sessions.resume",
        "sessions.stop",
    }:
        status_by_key = {
            "sessions.start": "running",
            "sessions.pause": "paused",
            "sessions.resume": "running",
            "sessions.stop": "stopped",
        }
        return json_response(200, session_payload(status=status_by_key.get(key, "running")))
    if key == "sessions.exec":
        return json_response(
            200,
            {
                "exit_code": 7,
                "stdout": "output",
                "stderr": "",
                "duration_ms": 2,
                "stdout_truncated": False,
                "stderr_truncated": False,
            },
        )
    if key in {"sessions.checkpoint", "sessions.delete"}:
        return json_response(200, {"ok": True})
    if key == "sessions.open":
        value = "https://" + "session.runacode.cloud" + "/__runa/auth?t=" + "synthetic"
        return json_response(200, {"url": value})
    if key == "records.list":
        detail = {"nested": ["value"]}
        return json_response(
            200,
            [
                {
                    "id": SESSION_ID,
                    "session_id": SESSION_ID,
                    "kind": "event",
                    "summary": "summary",
                    "detail": detail,
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "id": SECOND_SESSION_ID,
                    "session_id": SESSION_ID,
                    "kind": "event",
                    "summary": "summary",
                    "detail": detail,
                    "created_at": "2026-01-01T00:00:00Z",
                },
            ],
        )
    if key == "me.get":
        return json_response(
            200,
            {
                "id": SESSION_ID,
                "email": "person@example.com",
                "workspace": {
                    "assigned": True,
                    "usage": {
                        "est_spend_usd": 1.25,
                        "est_remaining_usd": 8.75,
                        "note": "estimate",
                    },
                },
            },
        )
    raise AssertionError(key)


@pytest.mark.hermetic
def test_sync_client_guard_blocks_mutated_request_before_injected_dispatch(monkeypatch) -> None:
    original = client_module.prepare_request

    def mutated_prepare(**kwargs: object) -> PreparedRequest:
        return replace(original(**kwargs), origin="https://example.com")  # type: ignore[arg-type]

    monkeypatch.setattr(client_module, "prepare_request", mutated_prepare)
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_value", transport=recorder)
    with pytest.raises(ConfigError):
        client.sessions.list()
    assert recorder.calls == []


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_client_guard_blocks_mutated_request_before_injected_dispatch(
    monkeypatch,
) -> None:
    original = client_module.prepare_request

    def mutated_prepare(**kwargs: object) -> PreparedRequest:
        return replace(original(**kwargs), origin="https://example.com")  # type: ignore[arg-type]

    monkeypatch.setattr(client_module, "prepare_request", mutated_prepare)
    recorder = AsyncRecorder(operation_response)
    client = AsyncRuna._with_transport(api_key="runa_sk_value", transport=recorder)
    with pytest.raises(ConfigError):
        await client.sessions.list()
    assert recorder.calls == []


@pytest.mark.hermetic
@pytest.mark.parametrize(
    "returned_id",
    [
        SECOND_SESSION_ID,
        SECOND_SESSION_ID.upper(),
        f" {SESSION_ID}",
        f"{SESSION_ID} ",
    ],
)
def test_sync_get_rejects_non_exact_response_id_after_one_dispatch(returned_id: str) -> None:
    recorder = SyncRecorder(
        lambda request, context: (
            json_response(200, session_payload(returned_id))
            if request.operation_key == "sessions.get"
            else operation_response(request, context)
        )
    )
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    with pytest.raises(ApiError) as malformed:
        client.sessions.get(SESSION_ID)
    assert malformed.value.code == "malformed_response"
    assert len(recorder.calls) == 1


@pytest.mark.hermetic
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "returned_id",
    [SECOND_SESSION_ID, SECOND_SESSION_ID.upper(), f" {SESSION_ID}", f"{SESSION_ID} "],
)
async def test_async_get_rejects_non_exact_response_id_after_one_dispatch(
    returned_id: str,
) -> None:
    recorder = AsyncRecorder(
        lambda request, context: (
            json_response(200, session_payload(returned_id))
            if request.operation_key == "sessions.get"
            else operation_response(request, context)
        )
    )
    client = AsyncRuna._with_transport(api_key="runa_sk_synthetic", transport=recorder)
    with pytest.raises(ApiError) as malformed:
        await client.sessions.get(SESSION_ID)
    assert malformed.value.code == "malformed_response"
    assert len(recorder.calls) == 1


@pytest.mark.hermetic
def test_create_validates_projection_constraints() -> None:
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    for name in (" ", "雪", "x" * 80):
        client.sessions.create(name, SessionCreateOptions())
        assert recorder.calls[-1][0].body == {"name": name}
    client.sessions.create(
        "named",
        SessionCreateOptions(
            agent=SessionAgent.CODEX,
            vcpus=8,
            memory_mib=16384,
            allowed_hosts=["example.com"],
            runtime_port=65535,
        ),
    )
    assert recorder.calls[-1][0].body == {
        "name": "named",
        "agent": "codex",
        "vcpus": 8,
        "memory_mib": 16384,
        "allowed_hosts": ["example.com"],
        "runtime_port": 65535,
    }
    before = len(recorder.calls)
    with pytest.raises(ConfigError):
        client.sessions.create(
            "named",
            SessionCreateOptions(agent="not-an-agent"),  # type: ignore[arg-type]
        )
    assert len(recorder.calls) == before


@pytest.mark.hermetic
@pytest.mark.parametrize(
    "name,options",
    [
        ("", SessionCreateOptions()),
        ("x" * 81, SessionCreateOptions()),
        ("x", SessionCreateOptions(vcpus=True)),
        ("x", SessionCreateOptions(vcpus=0)),
        ("x", SessionCreateOptions(vcpus=9)),
        ("x", SessionCreateOptions(memory_mib=511)),
        ("x", SessionCreateOptions(memory_mib=16385)),
        ("x", SessionCreateOptions(runtime_port=0)),
        ("x", SessionCreateOptions(runtime_port=65536)),
        ("x", SessionCreateOptions(allowed_hosts=())),
        ("x", SessionCreateOptions(allowed_hosts=[""])),
        ("x", SessionCreateOptions(allowed_hosts=["host"] * 129)),
        (
            "x",
            SessionCreateOptions(
                allowed_hosts=["example.com"],
                outbound_policy=OutboundPolicy(OutboundPolicyMode.ALLOWLIST, []),
            ),
        ),
        (
            "x",
            SessionCreateOptions(
                outbound_policy=OutboundPolicy(OutboundPolicyMode.DENYLIST, ["EXAMPLE.COM"])
            ),
        ),
        (
            "x",
            SessionCreateOptions(
                outbound_policy=OutboundPolicy(
                    OutboundPolicyMode.DENYLIST, ["example.com", "example.com"]
                )
            ),
        ),
    ],
)
def test_create_invalid_projection_vectors_do_not_dispatch(
    name: str, options: SessionCreateOptions
) -> None:
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    with pytest.raises(ConfigError):
        client.sessions.create(name, options)
    assert recorder.calls == []


@pytest.mark.hermetic
def test_create_snapshots_mutable_allowed_hosts() -> None:
    hosts = ["example.com"]
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    client.sessions.create("name", SessionCreateOptions(allowed_hosts=hosts))
    hosts.append("later.example")
    assert recorder.calls[-1][0].body == {"name": "name", "allowed_hosts": ["example.com"]}


@pytest.mark.hermetic
def test_create_serializes_and_snapshots_explicit_outbound_modes() -> None:
    hosts = ["tracking.example.com", "*.phishing.test"]
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    client.sessions.create(
        "deny",
        SessionCreateOptions(
            outbound_policy=OutboundPolicy(OutboundPolicyMode.DENYLIST, hosts)
        ),
    )
    hosts[0] = "changed.example.com"
    client.sessions.create(
        "allow-empty",
        SessionCreateOptions(
            outbound_policy=OutboundPolicy(OutboundPolicyMode.ALLOWLIST, [])
        ),
    )
    assert recorder.calls[-2][0].body == {
        "name": "deny",
        "outbound_policy": {
            "mode": "denylist",
            "hosts": ["tracking.example.com", "*.phishing.test"],
        },
    }
    assert recorder.calls[-1][0].body == {
        "name": "allow-empty",
        "outbound_policy": {"mode": "allowlist", "hosts": []},
    }


@pytest.mark.hermetic
def test_sync_public_surface_executes_all_13_exact_operations() -> None:
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    assert client.sessions is client.sessions
    assert client.records is client.records

    created = client.sessions.create(
        "example",
        SessionCreateOptions(
            agent=SessionAgent.CODEX,
            vcpus=2,
            memory_mib=1024,
            allowed_hosts=["example.com"],
            runtime_port=8080,
        ),
    )
    assert created.snapshot.status is SessionStatus.RUNNING
    listed = client.sessions.list()
    assert [item.id for item in listed] == [SESSION_ID, SECOND_SESSION_ID]
    assert client.sessions.get(SESSION_ID).id == SESSION_ID
    assert created.start() is created
    assert created.pause() is created and created.snapshot.status is SessionStatus.PAUSED
    assert created.resume() is created
    assert created.stop() is created and created.snapshot.status is SessionStatus.STOPPED
    result = created.exec(["tool", "--flag"], ExecOptions(cwd="/work", timeout_secs=1))
    assert result.exit_code == 7
    assert created.checkpoint("one").ok is True
    snapshot_before = created.snapshot
    assert created.open().url.endswith("synthetic")
    assert created.snapshot is snapshot_before
    assert created.delete().ok is True
    assert created.snapshot is snapshot_before
    assert len(client.records.list()) == 2
    assert client.me().workspace.usage.estimated_remaining_usd == 8.75  # type: ignore[union-attr]

    assert [request.operation_key for request, _ in recorder.calls] == [
        "sessions.create",
        "sessions.list",
        "sessions.get",
        "sessions.start",
        "sessions.pause",
        "sessions.resume",
        "sessions.stop",
        "sessions.exec",
        "sessions.checkpoint",
        "sessions.open",
        "sessions.delete",
        "records.list",
        "me.get",
    ]
    assert all(
        context.request_id.startswith("runa_req_") and len(context.request_id) == 41
        for _, context in recorder.calls
    )
    assert all("runa_req_" not in request.headers for request, _ in recorder.calls)
    client.close()
    client.close()
    with pytest.raises(RuntimeError, match=r"^Runa client is closed\.$"):
        client.me()


@pytest.mark.hermetic
def test_sync_refresh_identity_success_and_failure_cache_rules() -> None:
    responses = [json_response(200, session_payload())]

    def responder(request: PreparedRequest, context: RequestContext) -> RawResponse:
        del request, context
        return responses.pop(0)

    recorder = SyncRecorder(responder)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    handle = client.sessions.get(SESSION_ID)
    prior = handle.snapshot
    responses.append(json_response(500, {"error": "ignored"}))
    with pytest.raises(ApiError):
        handle.refresh()
    assert handle.snapshot is prior
    responses.append(json_response(200, session_payload(status="paused")))
    assert handle.refresh() is handle
    assert handle.snapshot.status is SessionStatus.PAUSED
    assert all(call[0].operation_key == "sessions.get" for call in recorder.calls)


@pytest.mark.hermetic
def test_sync_lifecycle_rejects_mismatched_identity_without_cache_mutation() -> None:
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    handle = client.sessions.get(SESSION_ID)
    prior = handle.snapshot
    recorder.responder = lambda _request, _context: json_response(
        200, session_payload(SECOND_SESSION_ID)
    )
    with pytest.raises(ApiError) as malformed:
        handle.start()
    assert malformed.value.code == "malformed_response"
    assert handle.snapshot is prior


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_lifecycle_rejects_mismatched_identity_without_cache_mutation() -> None:
    recorder = AsyncRecorder(lambda request, context: operation_response(request, context))
    client = AsyncRuna._with_transport(api_key="runa_sk_synthetic", transport=recorder)
    handle = await client.sessions.get(SESSION_ID)
    prior = handle.snapshot
    recorder.responder = lambda _request, _context: json_response(
        200, session_payload(SECOND_SESSION_ID)
    )
    with pytest.raises(ApiError) as malformed:
        await handle.start()
    assert malformed.value.code == "malformed_response"
    assert handle.snapshot is prior


@pytest.mark.hermetic
@pytest.mark.parametrize(
    "value",
    [
        "00000000-0000-0000-0000-00000000000G",
        "00000000-0000-0000-0000-000000000000 ",
        "{00000000-0000-0000-0000-000000000000}",
        7,
    ],
)
def test_invalid_get_id_has_zero_dispatch(value: object) -> None:
    recorder = SyncRecorder()
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    with pytest.raises(ConfigError):
        client.sessions.get(value)  # type: ignore[arg-type]
    assert recorder.calls == []


@pytest.mark.hermetic
def test_uuid_version_and_variant_nibbles_are_not_overvalidated() -> None:
    recorder = SyncRecorder(
        lambda _request, _context: json_response(
            200, session_payload("ffffffff-ffff-0fff-ffff-ffffffffffff")
        )
    )
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    assert (
        client.sessions.get("ffffffff-ffff-0fff-ffff-ffffffffffff").id
        == "ffffffff-ffff-0fff-ffff-ffffffffffff"
    )


@pytest.mark.hermetic
@pytest.mark.parametrize(
    "command,options",
    [
        ([], ExecOptions()),
        ("", ExecOptions()),
        ([""], ExecOptions()),
        ([b"bytes"], ExecOptions()),
        (["ok", 1], ExecOptions()),
        ("ok", ExecOptions(cwd=1)),  # type: ignore[arg-type]
        ("ok", ExecOptions(timeout_secs=True)),
        ("ok", ExecOptions(timeout_secs=0)),
        ("ok", ExecOptions(timeout_secs=601)),
        ("ok", ExecOptions(timeout_secs=1.5)),  # type: ignore[arg-type]
    ],
)
def test_exec_invalid_vectors_are_local(command, options) -> None:
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    synthetic = client.sessions.get(SESSION_ID)
    recorder.calls.clear()
    with pytest.raises(ConfigError):
        synthetic.exec(command, options)
    assert recorder.calls == []


@pytest.mark.hermetic
def test_checkpoint_rejects_non_schema_names() -> None:
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    handle = client.sessions.get(SESSION_ID)
    recorder.calls.clear()
    for value in (object(), "", "x" * 81, None, 1):
        with pytest.raises(ConfigError):
            handle.checkpoint(value)
    assert recorder.calls == []
    assert recorder.calls == []


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_surface_parity_and_close() -> None:
    recorder = AsyncRecorder(lambda request, context: operation_response(request, context))
    client = AsyncRuna._with_transport(
        api_key="runa_sk_synthetic",
        transport=recorder,
    )
    assert client.sessions is client.sessions
    created = await client.sessions.create("example", SessionCreateOptions())
    assert [item.id for item in await client.sessions.list()] == [SESSION_ID, SECOND_SESSION_ID]
    assert (await client.sessions.get(SESSION_ID)).id == SESSION_ID
    assert await created.start() is created
    assert await created.pause() is created
    assert await created.resume() is created
    assert await created.stop() is created
    assert (await created.exec("echo")).exit_code == 7
    assert (await created.checkpoint("named")).ok is True
    assert (await created.open()).url.endswith("synthetic")
    assert (await created.delete()).ok is True
    assert len(await client.records.list()) == 2
    assert (await client.me()).email == "person@example.com"
    assert len(recorder.calls) == 13
    await asyncio.gather(client.close(), client.close())
    with pytest.raises(RuntimeError, match=r"^Runa client is closed\.$"):
        await client.me()


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_cancellation_is_native_and_has_no_late_decode() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def held(_request: PreparedRequest, context: RequestContext) -> RawResponse:
        assert not context.cancellation_requested()
        started.set()
        await release.wait()
        return json_response(200, [])

    recorder = AsyncRecorder(held)
    client = AsyncRuna._with_transport(api_key="runa_sk_synthetic", transport=recorder)
    task = asyncio.create_task(client.sessions.list())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()
    await asyncio.sleep(0)
    assert len(recorder.calls) == 1
    await client.close()

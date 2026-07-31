from __future__ import annotations

import asyncio
import json
from types import MappingProxyType

import pytest

from runa import (
    AsyncRuna,
    ExecOptions,
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
                    "created_at": "time",
                },
                {
                    "id": SECOND_SESSION_ID,
                    "session_id": SESSION_ID,
                    "kind": "event",
                    "summary": "summary",
                    "detail": detail,
                    "created_at": "time",
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
def test_sync_public_surface_executes_all_13_exact_operations() -> None:
    recorder = SyncRecorder(operation_response)
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    assert client.sessions is client.sessions
    assert client.records is client.records

    created = client.sessions.create(
        "example",
        SessionCreateOptions(
            agent=SessionAgent.CODEX,
            vcpus=None,
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
    assert created.checkpoint({"name": ["one"]}).ok is True
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
        ([b"bytes"], ExecOptions()),
        (["ok", 1], ExecOptions()),
        ("", ExecOptions()),
        ("ok", ExecOptions(cwd=1)),  # type: ignore[arg-type]
        ("ok", ExecOptions(timeout_secs=True)),
        ("ok", ExecOptions(timeout_secs=0)),
        ("ok", ExecOptions(timeout_secs=601)),
        ("ok", ExecOptions(timeout_secs=1.5)),  # type: ignore[arg-type]
    ],
)
def test_exec_invalid_vectors_are_local(command, options) -> None:
    recorder = SyncRecorder()
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    handle = client.sessions.get  # avoid constructing a handle through transport
    from runa.client import Session

    synthetic = Session(
        client.sessions,
        __import__("runa").SessionSnapshot(
            SESSION_ID,
            "u",
            "s",
            "n",
            None,
            1,
            512,
            SessionStatus.RUNNING,
            0,
            "c",
            "u",
            "https://s.runacode.cloud",
        ),
        Session._TOKEN,
    )
    del handle
    with pytest.raises(ConfigError):
        synthetic.exec(command, options)
    assert recorder.calls == []


@pytest.mark.hermetic
def test_checkpoint_rejects_non_json_and_cycles() -> None:
    recorder = SyncRecorder()
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    from runa.client import Session

    snapshot = session_payload()
    handle = Session(
        client.sessions,
        __import__("runa").SessionSnapshot(
            snapshot["id"],
            snapshot["user_id"],
            snapshot["slug"],
            snapshot["name"],
            SessionAgent.CODEX,
            snapshot["vcpus"],
            snapshot["memory_mib"],
            SessionStatus.RUNNING,
            snapshot["running_seconds"],
            snapshot["created_at"],
            snapshot["updated_at"],
            snapshot["url"],
        ),
        Session._TOKEN,
    )
    circular: list[object] = []
    circular.append(circular)
    for value in (object(), (1,), {1: "x"}, float("inf"), circular):
        with pytest.raises(TypeError, match="checkpoint name must be JSON-admissible"):
            handle.checkpoint(value)
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
    assert (await created.checkpoint(None)).ok is True
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


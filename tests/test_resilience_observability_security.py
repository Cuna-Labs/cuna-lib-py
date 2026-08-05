from __future__ import annotations

import asyncio
import threading
import time

import httpx
import pytest

from runa import Runa
from runa._internal.contract import OPERATIONS, decode_for_operation
from runa._internal.contract.bridge import DecodeFailure, sanitize_response
from runa._internal.observability import NullObserver, OperationObserver
from runa._internal.resilience import (
    _MAX_SYNC_DISPATCH_THREADS,
    AbandonedSyncDispatchError,
    _dispatch_with_timeout,
    _open_sync_dispatch_threads,
    _total_deadline_for,
    deadline_for,
    full_jitter_delay,
    run_async,
    run_sync,
)
from runa._internal.security import (
    contains_denied,
    normalize_retained_text,
    retained_content_category,
)
from runa._internal.transport import ResponseStartedTransportError
from runa.errors import ApiError

from .support import SyncRecorder, json_response


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds

    async def async_sleep(self, seconds: float) -> None:
        self.value += seconds


class RecordingObserver:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []
        self.attempts = 0

    def attempt_start(self, attempt: int) -> None:
        self.attempts = attempt
        self.events.append(("attempt", attempt))

    def retry_scheduled(self, attempt: int, delay_ms: int) -> None:
        self.events.append(("retry", attempt, delay_ms))

    def end(self, outcome: str, error: BaseException | None = None) -> None:
        self.events.append(("end", outcome, type(error).__name__ if error else None))


@pytest.mark.hermetic
def test_exact_rejection_sampled_full_jitter() -> None:
    rejection = ((1 << 32) // 101) * 101
    values = iter([rejection, 37])
    assert full_jitter_delay(100, lambda: next(values)) == 37
    assert full_jitter_delay(200, lambda: 151) == 151
    assert full_jitter_delay(100, lambda: 0) == 0
    assert full_jitter_delay(100, lambda: ((1 << 32) // 101) * 101 - 1) <= 100
    with pytest.raises(ValueError):
        full_jitter_delay(100, lambda: -1)


@pytest.mark.hermetic
def test_read_retries_twice_with_immutable_policy_and_exact_jitter() -> None:
    clock = FakeClock()
    observer = RecordingObserver()
    calls: list[float] = []
    random_values = iter([((1 << 32) // 101) * 101, 37, 151])

    def dispatch(timeout: float) -> str:
        calls.append(timeout)
        if len(calls) < 3:
            raise httpx.TransportError("safe")
        return "done"

    result = run_sync(
        "sessions.get",
        dispatch,
        observer,  # type: ignore[arg-type]
        monotonic=clock,
        sleep=clock.sleep,
        raw_uint32=lambda: next(random_values),
    )
    assert result == "done"
    assert calls == [10.0, 10.0, 10.0]
    assert observer.events == [
        ("attempt", 1),
        ("retry", 2, 37),
        ("attempt", 2),
        ("retry", 3, 151),
        ("attempt", 3),
    ]


@pytest.mark.hermetic
def test_response_started_failures_and_writes_never_retry() -> None:
    for operation, error in (
        ("sessions.list", ResponseStartedTransportError("safe")),
        ("sessions.create", httpx.TransportError("safe")),
        ("sessions.open", httpx.TimeoutException("safe")),
    ):
        calls = 0

        def dispatch(_timeout: float, raised: BaseException = error) -> None:
            nonlocal calls
            calls += 1
            raise raised

        with pytest.raises(type(error)):
            run_sync(operation, dispatch, RecordingObserver())  # type: ignore[arg-type]
        assert calls == 1


@pytest.mark.hermetic
def test_sync_custom_transport_has_an_executable_wall_clock_boundary() -> None:
    release = threading.Event()
    started = time.perf_counter()
    with pytest.raises(httpx.TimeoutException):
        _dispatch_with_timeout(lambda _timeout: release.wait(), 0.01)
    assert time.perf_counter() - started < 0.2
    assert _open_sync_dispatch_threads() == 1
    release.set()
    for _ in range(100):
        if _open_sync_dispatch_threads() == 0:
            break
        time.sleep(0.001)
    assert _open_sync_dispatch_threads() == 0


@pytest.mark.hermetic
def test_sync_timeout_thread_retention_is_strictly_bounded() -> None:
    release = threading.Event()
    for _ in range(_MAX_SYNC_DISPATCH_THREADS):
        with pytest.raises(httpx.TimeoutException):
            _dispatch_with_timeout(lambda _timeout: release.wait(), 0.002)
    assert _open_sync_dispatch_threads() == _MAX_SYNC_DISPATCH_THREADS
    started = time.perf_counter()
    with pytest.raises(httpx.TimeoutException, match="capacity"):
        _dispatch_with_timeout(lambda _timeout: release.wait(), 1)
    assert time.perf_counter() - started < 0.1
    assert _open_sync_dispatch_threads() == _MAX_SYNC_DISPATCH_THREADS
    release.set()
    for _ in range(100):
        if _open_sync_dispatch_threads() == 0:
            break
        time.sleep(0.001)
    assert _open_sync_dispatch_threads() == 0


@pytest.mark.hermetic
def test_abandoned_sync_dispatch_is_never_retried_or_overlapped(monkeypatch) -> None:
    release = threading.Event()
    active = 0
    maximum_active = 0
    calls = 0
    monkeypatch.setattr("runa._internal.resilience.deadline_for", lambda *_args: 0.01)

    def blocked(_timeout: float) -> str:
        nonlocal active, calls, maximum_active
        calls += 1
        active += 1
        maximum_active = max(maximum_active, active)
        release.wait()
        active -= 1
        return "late-result-must-be-discarded"

    started = time.perf_counter()
    with pytest.raises(AbandonedSyncDispatchError):
        run_sync(
            "sessions.list",
            blocked,
            RecordingObserver(),  # type: ignore[arg-type]
            monotonic=time.monotonic,
        )
    assert time.perf_counter() - started < 0.2
    assert calls == 1
    assert maximum_active == 1
    assert _open_sync_dispatch_threads() == 1
    release.set()
    for _ in range(100):
        if _open_sync_dispatch_threads() == 0:
            break
        time.sleep(0.001)
    assert _open_sync_dispatch_threads() == 0


@pytest.mark.hermetic
def test_sync_deadline_helper_propagates_results_and_errors() -> None:
    assert _dispatch_with_timeout(lambda timeout: timeout, 0.1) == 0.1
    with pytest.raises(ValueError, match="safe"):
        _dispatch_with_timeout(lambda _timeout: (_ for _ in ()).throw(ValueError("safe")), 0.1)
    assert deadline_for("me.get") == 10
    assert deadline_for("sessions.agentAuth") == 30
    assert _total_deadline_for("me.get") == 30
    assert _total_deadline_for("sessions.agentAuth") == 90
    assert deadline_for("sessions.create") == 90
    assert deadline_for("sessions.exec", 7) == 22
    assert deadline_for("sessions.stop") == 60


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_retry_and_cancellation_policy() -> None:
    clock = FakeClock()
    observer = RecordingObserver()
    calls = 0

    async def dispatch(_timeout: float) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.TransportError("safe")
        return "done"

    assert (
        await run_async(
            "me.get",
            dispatch,
            observer,  # type: ignore[arg-type]
            monotonic=clock,
            sleep=clock.async_sleep,
            raw_uint32=lambda: 0,
        )
        == "done"
    )
    assert calls == 2

    async def cancelled(_timeout: float) -> str:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await run_async("me.get", cancelled, RecordingObserver())  # type: ignore[arg-type]


class Span:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self.events = events

    def add_event(self, name: str, attributes: object) -> None:
        self.events.append((name, attributes))

    def end(self, attributes: object) -> None:
        self.events.append(("span.end", attributes))


class Trace:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self.events = events

    def start_span(self, name: str, attributes: object) -> Span:
        self.events.append((name, attributes))
        return Span(self.events)


@pytest.mark.hermetic
def test_observability_order_schema_immutability_and_hook_isolation() -> None:
    diagnostic: list[object] = []
    trace_events: list[tuple[str, object]] = []
    times = iter([1.0, 1.037])
    observer = OperationObserver(
        OPERATIONS["sessions.list"],
        diagnostic.append,
        Trace(trace_events),
        clock=lambda: next(times),
        request_id="runa_req_" + "a" * 32,
    )
    observer.attempt_start(1)
    observer.retry_scheduled(2, 37)
    observer.attempt_start(2)
    observer.end("success")
    assert [event["name"] for event in diagnostic] == [  # type: ignore[index]
        "operation.start",
        "attempt.start",
        "retry.scheduled",
        "attempt.start",
        "operation.end",
    ]
    assert [name for name, _ in trace_events] == [
        "runa.sdk.operation",
        "operation.start",
        "attempt.start",
        "retry.scheduled",
        "attempt.start",
        "operation.end",
        "span.end",
    ]
    with pytest.raises(TypeError):
        diagnostic[0]["new"] = "value"  # type: ignore[index]
    assert all(
        set(event)
        <= {
            "name",
            "severity",
            "request_id",
            "operation_key",
            "method",
            "relative_path_template",
            "sdk_language",
            "sdk_version",
            "attempt",
            "delay_ms",
            "elapsed_ms",
            "outcome",
            "error_code",
            "http_status",
        }
        for event in diagnostic  # type: ignore[union-attr]
    )

    def broken(_event: object) -> None:
        raise RuntimeError("must be suppressed")

    isolated = OperationObserver(OPERATIONS["me.get"], broken, None)
    isolated.attempt_start(1)
    isolated.end("error", ApiError(500))


@pytest.mark.hermetic
@pytest.mark.asyncio
async def test_observation_hooks_ignore_async_and_object_sink_failures() -> None:
    class AwaitableSink:
        def __init__(self) -> None:
            self.closed = False

        def __await__(self):
            yield

        def close(self) -> None:
            self.closed = True

    awaitable = AwaitableSink()

    def returning_awaitable(_event: object) -> AwaitableSink:
        return awaitable

    async def async_span(_name: str, _attributes: object) -> None:
        return None

    class AsyncTrace:
        start_span = staticmethod(async_span)

    observer = OperationObserver(
        OPERATIONS["me.get"],
        returning_awaitable,
        AsyncTrace(),
        clock=lambda: 1.0,
        request_id_factory=lambda: "runa_req_" + "b" * 32,
    )
    observer.attempt_start(1)
    observer.end("cancelled")
    assert awaitable.closed is True

    emitted: list[object] = []

    class Emitter:
        def emit(self, event: object) -> None:
            emitted.append(event)

    object_sink = OperationObserver(OPERATIONS["me.get"], Emitter(), object())
    object_sink.end("error", RuntimeError("safe"))
    assert len(emitted) == 2

    null = NullObserver("runa_req_" + "c" * 32)
    null.attempt_start(2)
    null.retry_scheduled(3, 1)
    null.end("success")
    assert null.attempts == 2


@pytest.mark.security
@pytest.mark.parametrize(
    "value",
    [
        "http://session.runacode.cloud/__runa/auth?t=x",
        "https://session.runacode.cloud:443/__runa/auth?t=x",
        "https://user@session.runacode.cloud/__runa/auth?t=x",
        "https://session.extra.runacode.cloud/__runa/auth?t=x",
        "https://session.runacode.cloud/other?t=x",
        "https://session.runacode.cloud/__runa/auth?t=",
        "https://session.runacode.cloud/__runa/auth?t=x&other=y",
        "https://session.runacode.cloud/__runa/auth?t=x#fragment",
    ],
)
def test_open_url_validator_rejects_hostile_shapes(value: str) -> None:
    with pytest.raises(DecodeFailure):
        decode_for_operation("sessions.open", {"url": value})


@pytest.mark.security
def test_boundary_decoder_rejects_unknown_before_content_filtering() -> None:
    marker = bytes((114, 117, 110, 116, 97)).decode()
    encoded = "".join(f"%{byte:02x}" for byte in marker.encode())
    with pytest.raises(DecodeFailure):
        sanitize_response(
            {"id": "safe", "unknown": encoded, "detail": {"nested": encoded}},
            ("id", "detail"),
        )


@pytest.mark.security
def test_shared_retained_content_policy_decodes_and_classifies() -> None:
    marker = bytes((114, 117, 110, 116, 97)).decode()
    encoded = "".join(f"%{byte:02x}" for byte in marker.encode())
    assert normalize_retained_text(encoded) == marker
    assert normalize_retained_text("\\u0052UNA").casefold() == "runa"
    assert retained_content_category(encoded) == "reserved-infrastructure"
    assert retained_content_category("runa_sk_abcdefgh") == "usable-api-key"
    assert retained_content_category("Authorization: Bearer abc") == "authorization-header"
    assert retained_content_category("-----BEGIN PRIVATE KEY") == "private-key"
    assert retained_content_category("https://example.test/open?token=abc") == "capability-url"
    assert retained_content_category({"safe": ["value", 1]}) is None
    assert retained_content_category("egress") is None
    assert retained_content_category(("safe", {"nested": "runa_sk_abcdefgh"})) == "usable-api-key"
    assert contains_denied({"nested": [encoded]}) is True
    assert contains_denied({"nested": ["safe"]}) is False


@pytest.mark.security
def test_public_errors_never_include_external_content() -> None:
    hostile = "runa_sk_" + "sensitive"
    recorder = SyncRecorder(lambda _request, _context: json_response(500, {"error": hostile}))
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    with pytest.raises(ApiError) as caught:
        client.me()
    observations = (str(caught.value), repr(caught.value), caught.value.args)
    assert all(hostile not in repr(value) for value in observations)

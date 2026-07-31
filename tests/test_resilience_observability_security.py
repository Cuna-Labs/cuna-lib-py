from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError

import httpx
import pytest

from runa import Runa
from runa._internal.contract import OPERATIONS, decode_for_operation
from runa._internal.contract.bridge import DecodeFailure, sanitize_response
from runa._internal.observability import OperationObserver
from runa._internal.resilience import full_jitter_delay, run_async, run_sync
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

        def dispatch(_timeout: float) -> None:
            nonlocal calls
            calls += 1
            raise error

        with pytest.raises(type(error)):
            run_sync(operation, dispatch, RecordingObserver())  # type: ignore[arg-type]
        assert calls == 1


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
def test_boundary_sanitizer_drops_encoded_denied_values_without_echo() -> None:
    marker = bytes((114, 117, 110, 116, 97)).decode()
    encoded = "".join(f"%{byte:02x}" for byte in marker.encode())
    carrier = sanitize_response(
        {"id": "safe", "unknown": "safe", "detail": {"nested": encoded}},
        ("id", "detail"),
    )
    assert carrier.known_fields == {"id": "safe"}  # type: ignore[union-attr]
    assert carrier.unrecognized_fields == {"unknown": "safe"}  # type: ignore[union-attr]
    assert marker not in repr(carrier).casefold()


@pytest.mark.security
def test_public_errors_never_include_external_content() -> None:
    hostile = "runa_sk_" + "sensitive"
    recorder = SyncRecorder(lambda _request, _context: json_response(500, {"error": hostile}))
    client = Runa(api_key="runa_sk_synthetic", transport=recorder)
    with pytest.raises(ApiError) as caught:
        client.me()
    observations = (str(caught.value), repr(caught.value), caught.value.args)
    assert all(hostile not in repr(value) for value in observations)


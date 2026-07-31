"""Exact operation retry and deadline policy."""

from __future__ import annotations

import asyncio
import queue
import secrets
import threading
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from .observability import NullObserver, OperationObserver
from .transport import ResponseStartedTransportError

T = TypeVar("T")

READS = frozenset({"me.get", "sessions.list", "sessions.get", "records.list"})
_UINT32_SPACE = 1 << 32
_MAX_SYNC_DISPATCH_THREADS = 8
_SYNC_DISPATCH_CAPACITY = threading.BoundedSemaphore(_MAX_SYNC_DISPATCH_THREADS)


def deadline_for(operation_key: str, timeout_secs: int | None = None) -> float:
    if operation_key in READS:
        return 10.0
    if operation_key == "sessions.create":
        return 90.0
    if operation_key == "sessions.exec":
        return float((120 if timeout_secs is None else timeout_secs) + 15)
    return 60.0


def _eligible(error: BaseException) -> bool:
    return isinstance(error, httpx.TransportError | httpx.TimeoutException) and not isinstance(
        error, ResponseStartedTransportError
    )


def full_jitter_delay(cap_ms: int, raw_uint32: Callable[[], int]) -> int:
    limit = cap_ms + 1
    rejection_limit = (_UINT32_SPACE // limit) * limit
    while True:
        raw = raw_uint32()
        if type(raw) is not int or not 0 <= raw < _UINT32_SPACE:
            raise ValueError("raw jitter source must return an unsigned 32-bit integer")
        if raw < rejection_limit:
            return raw % limit


def _secure_uint32() -> int:
    return secrets.randbits(32)


def _dispatch_with_timeout(dispatch: Callable[[float], T], timeout: float) -> T:
    """Enforce a bounded wall-clock/thread boundary for custom sync transports.

    A late transport result is discarded. At most eight timed-out calls may remain
    alive; further calls fail closed without allocating another thread.
    """

    completed: queue.SimpleQueue[tuple[bool, object]] = queue.SimpleQueue()
    if not _SYNC_DISPATCH_CAPACITY.acquire(blocking=False):
        raise httpx.TimeoutException("The Runa API sync dispatch capacity is exhausted.")

    def invoke() -> None:
        try:
            try:
                completed.put((True, dispatch(timeout)))
            except BaseException as error:
                completed.put((False, error))
        finally:
            _SYNC_DISPATCH_CAPACITY.release()

    worker = threading.Thread(target=invoke, name="runa-sync-dispatch", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise httpx.TimeoutException("The Runa API operation timed out.")
    succeeded, value = completed.get()
    if succeeded:
        return value  # type: ignore[return-value]
    raise value  # type: ignore[misc]


def _open_sync_dispatch_threads() -> int:
    """Return the observable number of retained SDK sync-dispatch workers."""

    return sum(
        thread.name == "runa-sync-dispatch" and thread.is_alive()
        for thread in threading.enumerate()
    )


def run_sync(
    operation_key: str,
    dispatch: Callable[[float], T],
    observer: OperationObserver | NullObserver,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    raw_uint32: Callable[[], int] = _secure_uint32,
    timeout_secs: int | None = None,
) -> T:
    attempts = 3 if operation_key in READS else 1
    total_deadline = 30.0 if operation_key in READS else deadline_for(operation_key, timeout_secs)
    attempt_deadline = deadline_for(operation_key, timeout_secs)
    started = monotonic()
    for attempt in range(1, attempts + 1):
        remaining = total_deadline - (monotonic() - started)
        if remaining <= 0:
            raise httpx.TimeoutException("The Runa API operation timed out.")
        observer.attempt_start(attempt)
        attempt_started = monotonic()
        try:
            result = _dispatch_with_timeout(dispatch, min(attempt_deadline, remaining))
            if (
                monotonic() - attempt_started > min(attempt_deadline, remaining)
                or monotonic() - started > total_deadline
            ):
                raise ResponseStartedTransportError("The Runa API operation timed out.")
            return result
        except BaseException as error:
            if not _eligible(error) or attempt >= attempts:
                raise
            delay_limit_ms = 100 * (2 ** (attempt - 1))
            delay_ms = full_jitter_delay(delay_limit_ms, raw_uint32)
            if monotonic() - started + delay_ms / 1000 >= total_deadline:
                raise
            observer.retry_scheduled(attempt + 1, delay_ms)
            sleep(delay_ms / 1000)
    raise AssertionError("unreachable")


async def run_async(
    operation_key: str,
    dispatch: Callable[[float], Awaitable[T]],
    observer: OperationObserver | NullObserver,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    raw_uint32: Callable[[], int] = _secure_uint32,
    timeout_secs: int | None = None,
) -> T:
    attempts = 3 if operation_key in READS else 1
    total_deadline = 30.0 if operation_key in READS else deadline_for(operation_key, timeout_secs)
    attempt_deadline = deadline_for(operation_key, timeout_secs)
    started = monotonic()
    for attempt in range(1, attempts + 1):
        remaining = total_deadline - (monotonic() - started)
        if remaining <= 0:
            raise httpx.TimeoutException("The Runa API operation timed out.")
        observer.attempt_start(attempt)
        attempt_started = monotonic()
        try:
            try:
                result = await asyncio.wait_for(
                    dispatch(min(attempt_deadline, remaining)),
                    timeout=min(attempt_deadline, remaining),
                )
                if (
                    monotonic() - attempt_started > min(attempt_deadline, remaining)
                    or monotonic() - started > total_deadline
                ):
                    raise ResponseStartedTransportError("The Runa API operation timed out.")
                return result
            except TimeoutError:
                raise httpx.TimeoutException("The Runa API operation timed out.") from None
        except asyncio.CancelledError:
            raise
        except BaseException as error:
            if not _eligible(error) or attempt >= attempts:
                raise
            delay_limit_ms = 100 * (2 ** (attempt - 1))
            delay_ms = full_jitter_delay(delay_limit_ms, raw_uint32)
            if monotonic() - started + delay_ms / 1000 >= total_deadline:
                raise
            observer.retry_scheduled(attempt + 1, delay_ms)
            await sleep(delay_ms / 1000)
    raise AssertionError("unreachable")

"""Exact operation retry and deadline policy."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from .observability import NullObserver, OperationObserver

T = TypeVar("T")

READS = frozenset({"me.get", "sessions.list", "sessions.get", "records.list"})


def deadline_for(operation_key: str, timeout_secs: int | None = None) -> float:
    if operation_key in READS:
        return 10.0
    if operation_key == "sessions.create":
        return 90.0
    if operation_key == "sessions.exec":
        return float((120 if timeout_secs is None else timeout_secs) + 15)
    return 60.0


def _eligible(error: BaseException) -> bool:
    return isinstance(error, (httpx.TransportError, httpx.TimeoutException))


def run_sync(
    operation_key: str,
    dispatch: Callable[[float], T],
    observer: OperationObserver | NullObserver,
    *,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    random_source: random.Random | None = None,
    timeout_secs: int | None = None,
) -> T:
    attempts = 3 if operation_key in READS else 1
    total_deadline = 30.0 if operation_key in READS else deadline_for(operation_key, timeout_secs)
    attempt_deadline = deadline_for(operation_key, timeout_secs)
    started = monotonic()
    rng = random_source or random.Random()
    for attempt in range(1, attempts + 1):
        remaining = total_deadline - (monotonic() - started)
        if remaining <= 0:
            raise httpx.TimeoutException("The Runa API operation timed out.")
        observer.attempt_start(attempt)
        try:
            return dispatch(min(attempt_deadline, remaining))
        except BaseException as error:
            if not _eligible(error) or attempt >= attempts:
                raise
            delay_limit_ms = 100 * (2 ** (attempt - 1))
            delay_ms = rng.randrange(delay_limit_ms + 1)
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
    random_source: random.Random | None = None,
    timeout_secs: int | None = None,
) -> T:
    attempts = 3 if operation_key in READS else 1
    total_deadline = 30.0 if operation_key in READS else deadline_for(operation_key, timeout_secs)
    attempt_deadline = deadline_for(operation_key, timeout_secs)
    started = monotonic()
    rng = random_source or random.Random()
    for attempt in range(1, attempts + 1):
        remaining = total_deadline - (monotonic() - started)
        if remaining <= 0:
            raise httpx.TimeoutException("The Runa API operation timed out.")
        observer.attempt_start(attempt)
        try:
            return await dispatch(min(attempt_deadline, remaining))
        except asyncio.CancelledError:
            raise
        except BaseException as error:
            if not _eligible(error) or attempt >= attempts:
                raise
            delay_limit_ms = 100 * (2 ** (attempt - 1))
            delay_ms = rng.randrange(delay_limit_ms + 1)
            if monotonic() - started + delay_ms / 1000 >= total_deadline:
                raise
            observer.retry_scheduled(attempt + 1, delay_ms)
            await sleep(delay_ms / 1000)
    raise AssertionError("unreachable")

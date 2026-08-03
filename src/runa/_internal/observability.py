"""Local, opt-in, omission-first operation observations."""

from __future__ import annotations

import inspect
import math
import time
import uuid
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import cast

from runa.errors import ApiError, RunaError

from .contract import Operation

SDK_VERSION = "0.1.0"


def _immutable(values: dict[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(values))


class OperationObserver:
    __slots__ = (
        "_clock",
        "_diagnostic_sink",
        "_operation",
        "_span",
        "_start_time",
        "_started",
        "attempts",
        "request_id",
    )

    def __init__(
        self,
        operation: Operation,
        diagnostic_sink: object | None,
        trace_sink: object | None,
        *,
        clock: Callable[[], float] = time.monotonic,
        request_id_factory: Callable[[], str] | None = None,
        request_id: str | None = None,
    ) -> None:
        self._operation = operation
        self._clock = clock
        self._diagnostic_sink = diagnostic_sink
        self._span: object | None = None
        self._start_time = clock()
        self._started = False
        self.attempts = 0
        self.request_id = request_id or (
            request_id_factory()
            if request_id_factory is not None
            else f"runa_req_{uuid.uuid4().hex}"
        )
        self._start(trace_sink)

    def _base(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "operation_key": self._operation.key,
            "method": self._operation.method,
            "relative_path_template": self._operation.path_template,
            "sdk_language": "python",
            "sdk_version": SDK_VERSION,
        }

    def _call(self, target: object, name: str, *args: object) -> object | None:
        try:
            function = getattr(target, name)
            if inspect.iscoroutinefunction(function):
                return None
            result = function(*args)
            if inspect.isawaitable(result):
                close = getattr(result, "close", None)
                if callable(close):
                    close()
                return None
            return cast(object | None, result)
        except BaseException:
            return None

    def _deliver(self, event: dict[str, object]) -> None:
        payload = _immutable(event)
        if self._span is not None:
            attrs = _immutable({key: value for key, value in event.items() if key != "name"})
            self._call(self._span, "add_event", event["name"], attrs)
        sink = self._diagnostic_sink
        if sink is None:
            return
        if callable(sink) and not inspect.iscoroutinefunction(sink):
            try:
                result = sink(payload)
                if inspect.isawaitable(result):
                    close = getattr(result, "close", None)
                    if callable(close):
                        close()
            except BaseException:  # noqa: S110 - hook failures are isolated by contract
                pass
        elif hasattr(sink, "emit"):
            self._call(sink, "emit", payload)

    def _start(self, trace_sink: object | None) -> None:
        event = {"name": "operation.start", "severity": "DEBUG", **self._base()}
        if trace_sink is not None and not inspect.iscoroutinefunction(
            getattr(trace_sink, "start_span", None)
        ):
            attrs = _immutable(
                {key: value for key, value in event.items() if key not in {"name", "severity"}}
            )
            self._span = self._call(trace_sink, "start_span", "runa.sdk.operation", attrs)
        self._deliver(event)
        self._started = True

    def attempt_start(self, attempt: int) -> None:
        self.attempts = attempt
        self._deliver(
            {
                "name": "attempt.start",
                "severity": "DEBUG",
                **self._base(),
                "attempt": attempt,
            }
        )

    def retry_scheduled(self, next_attempt: int, delay_ms: int) -> None:
        self._deliver(
            {
                "name": "retry.scheduled",
                "severity": "WARN",
                **self._base(),
                "attempt": next_attempt,
                "delay_ms": delay_ms,
            }
        )

    def end(self, outcome: str, error: BaseException | None = None) -> None:
        elapsed = max(0, math.floor((self._clock() - self._start_time) * 1000))
        event: dict[str, object] = {
            "name": "operation.end",
            "severity": (
                "INFO" if outcome == "success" else "WARN" if outcome == "cancelled" else "ERROR"
            ),
            **self._base(),
            "attempt": self.attempts,
            "elapsed_ms": elapsed,
            "outcome": outcome,
        }
        if outcome == "error" and isinstance(error, RunaError):
            event["error_code"] = error.code
            if isinstance(error, ApiError):
                event["http_status"] = error.status
        self._deliver(event)
        if self._span is not None:
            attrs = _immutable(
                {key: value for key, value in event.items() if key not in {"name", "severity"}}
            )
            self._call(self._span, "end", attrs)


class NullObserver:
    __slots__ = ("attempts", "request_id")

    def __init__(self, request_id: str | None = None) -> None:
        self.attempts = 0
        self.request_id = request_id or f"runa_req_{uuid.uuid4().hex}"

    def attempt_start(self, attempt: int) -> None:
        self.attempts = attempt

    def retry_scheduled(self, next_attempt: int, delay_ms: int) -> None:
        del next_attempt, delay_ms

    def end(self, outcome: str, error: BaseException | None = None) -> None:
        del outcome, error

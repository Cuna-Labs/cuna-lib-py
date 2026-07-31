from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from types import MappingProxyType

from runa._internal.transport import PreparedRequest, RawResponse, RequestContext

SESSION_ID = "00000000-0000-0000-0000-000000000000"
SECOND_SESSION_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def session_payload(session_id: str = SESSION_ID, *, status: str = "running") -> dict[str, object]:
    return {
        "id": session_id,
        "user_id": "user",
        "slug": "session",
        "name": "example",
        "agent": "codex",
        "vcpus": 2,
        "memory_mib": 1024,
        "status": status,
        "running_seconds": 5,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:01Z",
        "url": "https://session.runacode.cloud",
    }


def json_response(status: int, value: object, content_type: str = "application/json") -> RawResponse:
    return RawResponse(
        status,
        MappingProxyType({"content-type": content_type}),
        json.dumps(value, ensure_ascii=False).encode(),
    )


class SyncRecorder:
    def __init__(
        self,
        responder: Callable[[PreparedRequest, RequestContext], RawResponse] | None = None,
    ) -> None:
        self.calls: list[tuple[PreparedRequest, RequestContext]] = []
        self.responder = responder or (lambda _request, _context: json_response(200, {"ok": True}))

    def __call__(self, request: PreparedRequest, context: RequestContext) -> RawResponse:
        self.calls.append((request, context))
        return self.responder(request, context)


class AsyncRecorder:
    def __init__(
        self,
        responder: Callable[
            [PreparedRequest, RequestContext], Awaitable[RawResponse] | RawResponse
        ]
        | None = None,
    ) -> None:
        self.calls: list[tuple[PreparedRequest, RequestContext]] = []
        self.responder = responder

    async def __call__(self, request: PreparedRequest, context: RequestContext) -> RawResponse:
        self.calls.append((request, context))
        if self.responder is None:
            return json_response(200, {"ok": True})
        value = self.responder(request, context)
        if hasattr(value, "__await__"):
            return await value  # type: ignore[misc,no-any-return]
        return value


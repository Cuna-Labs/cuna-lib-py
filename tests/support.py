from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from types import MappingProxyType

from cuna._internal.transport import PreparedRequest, RawResponse, RequestContext

SESSION_ID = "00000000-0000-0000-0000-000000000000"
SECOND_SESSION_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def session_payload(session_id: str = SESSION_ID, *, status: str = "running") -> dict[str, object]:
    return {
        "id": session_id,
        "user_id": SECOND_SESSION_ID,
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


def json_response(
    status: int,
    value: object,
    content_type: str = "application/json",
    headers: dict[str, str] | None = None,
) -> RawResponse:
    return RawResponse(
        status,
        MappingProxyType({"content-type": content_type, **(headers or {})}),
        json.dumps(value, ensure_ascii=False).encode(),
    )


def capability_snapshot_payload(**overrides: object) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "subject_scope": "account",
        "observed_at": "2026-08-08T12:00:00.000Z",
        "expires_at": "2026-08-08T12:00:30.000Z",
        "etag": "a" * 64,
        "capabilities": [
            {
                "id": "agent_sessions.manage",
                "availability": "unsupported",
                "surfaces": ["cli", "web", "sdk"],
                "interaction": "native",
                "mutation_class": "reversible",
                "required_permissions": ["agent_sessions:manage"],
                "reason_code": "agent_session_foundation_not_available",
            }
        ],
        **overrides,
    }


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
        responder: Callable[[PreparedRequest, RequestContext], Awaitable[RawResponse] | RawResponse]
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

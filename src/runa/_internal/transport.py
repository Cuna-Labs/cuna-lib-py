"""Private sync/async HTTP adapters and strict response disposition."""

from __future__ import annotations

import json
import re
import ssl
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Protocol, cast

import httpx

from runa.errors import ApiError, ApiProblem, ConfigError, ProblemAction, WorkspaceSyncProblem

from .constraints import is_uuid

MAX_RESPONSE_BYTES = 16 * 1024 * 1024
USER_AGENT = "runa-sdk-python/0.1.0"
_PROBLEM_CODE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_PROBLEM_ORIGINS = ("https://api.getcuna.com", "https://api.runacode.io")
_WORKSPACE_SYNC_CODE = re.compile(r"^workspace_sync_[a-z0-9_]{2,48}$")
_WORKSPACE_SYNC_CAPABILITIES = frozenset(
    {
        "atomic_generation_commit",
        "bounded_manifest_pages",
        "content_digest_verification",
        "explicit_reconciliation",
        "ordered_generation_changes",
        "policy_bound_admission",
    }
)


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    operation_key: str
    method: str
    origin: str
    relative_path: str
    headers: Mapping[str, str]
    body: Mapping[str, object] | None
    body_bytes: bytes | None
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class RequestContext:
    operation_key: str
    request_id: str
    cancellation_requested: Callable[[], bool]


@dataclass(frozen=True, slots=True)
class RawResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class SyncTransport(Protocol):
    def __call__(self, request: PreparedRequest, context: RequestContext) -> RawResponse: ...


class AsyncTransport(Protocol):
    def __call__(
        self, request: PreparedRequest, context: RequestContext
    ) -> Awaitable[RawResponse]: ...


class ResponseStartedTransportError(httpx.TransportError):
    """Safe native failure after response headers; never retryable."""


def security_dispatch_guard(
    request: PreparedRequest,
    context: RequestContext,
    *,
    expected_origin: str,
    expected_operation_key: str,
    expected_method: str,
    expected_path: str,
) -> None:
    """Reject any prepared-request drift before a transport can perform I/O."""

    if (
        request.origin != expected_origin
        or request.operation_key != expected_operation_key
        or context.operation_key != expected_operation_key
        or request.method != expected_method
        or request.relative_path != expected_path
    ):
        raise ConfigError()


def prepare_request(
    *,
    operation_key: str,
    method: str,
    origin: str,
    relative_path: str,
    api_key: str,
    body: Mapping[str, object] | None,
    raw_body: bytes | None = None,
    idempotency_key: str | None = None,
    timeout_seconds: float,
) -> PreparedRequest:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json, application/problem+json",
    }
    if idempotency_key is not None:
        if re.fullmatch(r"[!-~]{8,128}", idempotency_key) is None:
            raise ConfigError()
        headers["Idempotency-Key"] = idempotency_key
    if body is not None and raw_body is not None:
        raise TypeError("Request value must use one media type.")
    body_bytes: bytes | None = raw_body
    if raw_body is not None:
        headers["Content-Type"] = "application/octet-stream"
        headers["Content-Length"] = str(len(raw_body))
    elif body is not None:
        try:
            body_bytes = json.dumps(
                body, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise TypeError("Request value must be JSON-admissible.") from None
        headers["Content-Type"] = "application/json; charset=utf-8"
    return PreparedRequest(
        operation_key=operation_key,
        method=method,
        origin=origin,
        relative_path=relative_path,
        headers=MappingProxyType(headers),
        body=MappingProxyType(dict(body)) if body is not None else None,
        body_bytes=body_bytes,
        timeout_seconds=timeout_seconds,
    )


def _problem(response: RawResponse) -> ApiProblem | WorkspaceSyncProblem | None:
    content_type = response.headers.get("content-type", response.headers.get("Content-Type", ""))
    if len(response.body) > MAX_RESPONSE_BYTES or content_type.split(";", 1)[
        0
    ].strip().lower() not in {"application/json", "application/problem+json"}:
        return None
    try:
        value = json.loads(response.body.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    generic_keys = {
        "type",
        "title",
        "status",
        "code",
        "request_id",
        "retryable",
        "detail",
        "action",
    }
    sync_keys = generic_keys | {"selected_protocol", "capabilities"}
    if not isinstance(value, dict) or set(value) not in {
        frozenset(generic_keys),
        frozenset(generic_keys - {"detail"}),
        frozenset(generic_keys - {"action"}),
        frozenset(generic_keys - {"detail", "action"}),
        frozenset(sync_keys),
    }:
        return None
    required = {"type", "title", "status", "code", "request_id", "retryable"}
    if not required <= set(value):
        return None
    code = value["code"]
    if (
        not isinstance(code, str)
        or _PROBLEM_CODE.fullmatch(code) is None
        or value["type"] not in {f"{origin}/problems/{code}" for origin in _PROBLEM_ORIGINS}
        or type(value["status"]) is not int
        or value["status"] != response.status
        or not 400 <= value["status"] <= 599
        or not isinstance(value["title"], str)
        or not 1 <= len(value["title"]) <= 120
        or not isinstance(value["request_id"], str)
        or not is_uuid(value["request_id"])
        or type(value["retryable"]) is not bool
        or (
            "detail" in value
            and (not isinstance(value["detail"], str) or len(value["detail"]) > 500)
        )
    ):
        return None
    try:
        action = ProblemAction(value["action"]) if "action" in value else None
    except (TypeError, ValueError):
        return None
    common = {
        "type": value["type"],
        "title": value["title"],
        "status": value["status"],
        "code": code,
        "request_id": value["request_id"],
        "retryable": value["retryable"],
        "detail": value.get("detail"),
        "action": action,
    }
    if set(value) == sync_keys:
        selected_protocol = value["selected_protocol"]
        capabilities = value["capabilities"]
        if (
            _WORKSPACE_SYNC_CODE.fullmatch(code) is None
            or action not in {ProblemAction.RETRY, ProblemAction.NONE}
            or not isinstance(value["detail"], str)
            or not value["detail"]
            or (selected_protocol is not None and type(selected_protocol) is not int)
            or selected_protocol not in (1, 2, None)
            or not isinstance(capabilities, list)
            or any(not isinstance(item, str) for item in capabilities)
            or len(capabilities) != len(set(capabilities))
            or (selected_protocol is None and capabilities != [])
            or (
                selected_protocol is not None
                and (
                    len(capabilities) != len(_WORKSPACE_SYNC_CAPABILITIES)
                    or set(capabilities) != _WORKSPACE_SYNC_CAPABILITIES
                )
            )
        ):
            return None
        return WorkspaceSyncProblem(
            **common,
            selected_protocol=cast(Literal[1, 2] | None, selected_protocol),
            capabilities=cast(
                tuple[
                    Literal[
                        "atomic_generation_commit",
                        "bounded_manifest_pages",
                        "content_digest_verification",
                        "explicit_reconciliation",
                        "ordered_generation_changes",
                        "policy_bound_admission",
                    ],
                    ...,
                ],
                tuple(capabilities),
            ),
        )
    return ApiProblem(**common)


def disposition(response: RawResponse, success_status: int) -> object:
    if response.status != success_status:
        if 200 <= response.status < 400:
            raise ApiError(response.status, code="malformed_response")
        raise ApiError(response.status, code="api_error", problem=_problem(response))
    if len(response.body) > MAX_RESPONSE_BYTES:
        raise ApiError(response.status, code="malformed_response")
    content_type = response.headers.get("content-type", response.headers.get("Content-Type", ""))
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise ApiError(response.status, code="malformed_response")
    try:
        text = response.body.decode("utf-8", errors="strict")
        return json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ApiError(response.status, code="malformed_response") from None


def _tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


class SyncHttpTransport:
    __slots__ = ("_client", "_closed")

    def __init__(self, base_url: str) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            follow_redirects=False,
            verify=_tls_context(),
            trust_env=False,
        )
        self._closed = False

    def __call__(self, request: PreparedRequest, context: RequestContext) -> RawResponse:
        del context
        if self._closed:
            raise RuntimeError("Runa client is closed.")
        try:
            with self._client.stream(
                request.method,
                request.relative_path,
                headers=dict(request.headers),
                content=request.body_bytes,
                timeout=request.timeout_seconds,
                follow_redirects=False,
            ) as response:
                collected = bytearray()
                try:
                    for chunk in response.iter_bytes():
                        if len(collected) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise ApiError(response.status_code, code="malformed_response")
                        collected.extend(chunk)
                except ApiError:
                    raise
                except httpx.TransportError:
                    raise ResponseStartedTransportError(
                        "The Runa API response stream failed."
                    ) from None
                return RawResponse(
                    response.status_code,
                    MappingProxyType(
                        {
                            "content-type": response.headers.get("content-type", ""),
                            "cache-control": response.headers.get("cache-control", ""),
                            "etag": response.headers.get("etag", ""),
                        }
                    ),
                    bytes(collected),
                )
        except ApiError:
            raise
        except ResponseStartedTransportError:
            raise
        except httpx.TimeoutException:
            raise httpx.TimeoutException("The Runa API transport timed out.") from None
        except httpx.TransportError:
            raise httpx.TransportError("The Runa API transport failed.") from None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._client.close()


class AsyncHttpTransport:
    __slots__ = ("_base_url", "_client", "_closed")

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._client: httpx.AsyncClient | None = None
        self._closed = False

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                follow_redirects=False,
                verify=_tls_context(),
                trust_env=False,
            )
        return self._client

    async def __call__(self, request: PreparedRequest, context: RequestContext) -> RawResponse:
        del context
        if self._closed:
            raise RuntimeError("Runa client is closed.")
        client = self._get_client()
        try:
            async with client.stream(
                request.method,
                request.relative_path,
                headers=dict(request.headers),
                content=request.body_bytes,
                timeout=request.timeout_seconds,
                follow_redirects=False,
            ) as response:
                collected = bytearray()
                try:
                    async for chunk in response.aiter_bytes():
                        if len(collected) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise ApiError(response.status_code, code="malformed_response")
                        collected.extend(chunk)
                except ApiError:
                    raise
                except httpx.TransportError:
                    raise ResponseStartedTransportError(
                        "The Runa API response stream failed."
                    ) from None
                return RawResponse(
                    response.status_code,
                    MappingProxyType(
                        {
                            "content-type": response.headers.get("content-type", ""),
                            "cache-control": response.headers.get("cache-control", ""),
                            "etag": response.headers.get("etag", ""),
                        }
                    ),
                    bytes(collected),
                )
        except ApiError:
            raise
        except ResponseStartedTransportError:
            raise
        except httpx.TimeoutException:
            raise httpx.TimeoutException("The Runa API transport timed out.") from None
        except httpx.TransportError:
            raise httpx.TransportError("The Runa API transport failed.") from None

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            client, self._client = self._client, None
            if client is not None:
                await client.aclose()


SyncTransportFactory = Callable[[str], SyncHttpTransport]
AsyncTransportFactory = Callable[[str], AsyncHttpTransport]

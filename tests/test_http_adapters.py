from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import ClassVar

import httpx
import pytest

from runa._internal.transport import (
    MAX_RESPONSE_BYTES,
    AsyncHttpTransport,
    PreparedRequest,
    RequestContext,
    ResponseStartedTransportError,
    SyncHttpTransport,
)
from runa.errors import ApiError


def request() -> PreparedRequest:
    return PreparedRequest(
        "sessions.list",
        "GET",
        "https://api.runacode.io",
        "/v1/sessions",
        {"Accept": "application/json"},
        None,
        None,
        1,
    )


def context() -> RequestContext:
    return RequestContext("sessions.list", "runa_req_" + "a" * 32, lambda: False)


class SyncResponse:
    status_code = 200
    headers: ClassVar[dict[str, str]] = {"content-type": "application/json"}

    def __init__(self, chunks: list[bytes] | BaseException) -> None:
        self.chunks = chunks

    def __enter__(self) -> SyncResponse:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def iter_bytes(self) -> Iterator[bytes]:
        if isinstance(self.chunks, BaseException):
            raise self.chunks
        yield from self.chunks


class SyncClient:
    def __init__(self, response: SyncResponse | BaseException) -> None:
        self.response = response
        self.closed = False

    def stream(self, *args: object, **kwargs: object) -> SyncResponse:
        del args, kwargs
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response

    def close(self) -> None:
        self.closed = True


@pytest.mark.hermetic
def test_sync_http_adapter_success_close_and_safe_failures(monkeypatch) -> None:
    fake = SyncClient(SyncResponse([b"{}", b"\n"]))
    monkeypatch.setattr(httpx, "Client", lambda **_kwargs: fake)
    transport = SyncHttpTransport("https://api.runacode.io")
    response = transport(request(), context())
    assert response.body == b"{}\n"
    transport.close()
    transport.close()
    assert fake.closed is True
    with pytest.raises(RuntimeError):
        transport(request(), context())

    for native, expected in (
        (httpx.TimeoutException("unsafe"), httpx.TimeoutException),
        (httpx.TransportError("unsafe"), httpx.TransportError),
    ):
        fake = SyncClient(native)
        monkeypatch.setattr(httpx, "Client", lambda _fake=fake, **_kwargs: _fake)
        with pytest.raises(expected, match="Runa API transport"):
            SyncHttpTransport("https://api.runacode.io")(request(), context())

    fake = SyncClient(SyncResponse(httpx.TransportError("unsafe")))
    monkeypatch.setattr(httpx, "Client", lambda **_kwargs: fake)
    with pytest.raises(ResponseStartedTransportError):
        SyncHttpTransport("https://api.runacode.io")(request(), context())

    fake = SyncClient(SyncResponse([b"x" * (MAX_RESPONSE_BYTES + 1)]))
    monkeypatch.setattr(httpx, "Client", lambda **_kwargs: fake)
    with pytest.raises(ApiError):
        SyncHttpTransport("https://api.runacode.io")(request(), context())


class AsyncResponse:
    status_code = 200
    headers: ClassVar[dict[str, str]] = {"content-type": "application/json"}

    def __init__(self, chunks: list[bytes] | BaseException) -> None:
        self.chunks = chunks

    async def __aenter__(self) -> AsyncResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        del args

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        if isinstance(self.chunks, BaseException):
            raise self.chunks
        for chunk in self.chunks:
            yield chunk


class AsyncClient:
    def __init__(self, response: AsyncResponse | BaseException, **kwargs: object) -> None:
        del kwargs
        self.response = response
        self.closed = False

    def stream(self, *args: object, **kwargs: object) -> AsyncResponse:
        del args, kwargs
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_http_adapter_success_close_and_safe_failures(monkeypatch) -> None:
    fake = AsyncClient(AsyncResponse([b"{}"]))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: fake)
    transport = AsyncHttpTransport("https://api.runacode.io")
    assert (await transport(request(), context())).body == b"{}"
    await transport.close()
    await transport.close()
    assert fake.closed is True
    with pytest.raises(RuntimeError):
        await transport(request(), context())

    for native, expected in (
        (httpx.TimeoutException("unsafe"), httpx.TimeoutException),
        (httpx.TransportError("unsafe"), httpx.TransportError),
    ):
        fake = AsyncClient(native)
        monkeypatch.setattr(httpx, "AsyncClient", lambda _fake=fake, **_kwargs: _fake)
        with pytest.raises(expected, match="Runa API transport"):
            await AsyncHttpTransport("https://api.runacode.io")(request(), context())

    fake = AsyncClient(AsyncResponse(httpx.TransportError("unsafe")))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: fake)
    with pytest.raises(ResponseStartedTransportError):
        await AsyncHttpTransport("https://api.runacode.io")(request(), context())

    fake = AsyncClient(AsyncResponse([b"x" * (MAX_RESPONSE_BYTES + 1)]))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: fake)
    with pytest.raises(ApiError):
        await AsyncHttpTransport("https://api.runacode.io")(request(), context())

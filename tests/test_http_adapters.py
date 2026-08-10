from __future__ import annotations

import ssl
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
        {"Accept": "application/json, application/problem+json"},
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
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def stream(self, *args: object, **kwargs: object) -> SyncResponse:
        self.calls.append((args, kwargs))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response

    def close(self) -> None:
        self.closed = True


@pytest.mark.hermetic
def test_sync_http_adapter_success_close_and_safe_failures(monkeypatch) -> None:
    fake = SyncClient(SyncResponse([b"{}", b"\n"]))
    client_options: list[dict[str, object]] = []

    def client_factory(**kwargs: object) -> SyncClient:
        client_options.append(kwargs)
        return fake

    monkeypatch.setattr(httpx, "Client", client_factory)
    transport = SyncHttpTransport("https://api.runacode.io")
    response = transport(request(), context())
    assert response.body == b"{}\n"
    assert len(client_options) == 1
    options = client_options[0]
    assert options["base_url"] == "https://api.runacode.io"
    assert options["follow_redirects"] is False
    assert options["trust_env"] is False
    tls = options["verify"]
    assert isinstance(tls, ssl.SSLContext)
    assert tls.minimum_version is ssl.TLSVersion.TLSv1_2
    assert tls.check_hostname is True
    assert tls.verify_mode is ssl.CERT_REQUIRED
    assert fake.calls[0][0][:2] == ("GET", "/v1/sessions")
    assert fake.calls[0][1]["follow_redirects"] is False
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
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def stream(self, *args: object, **kwargs: object) -> AsyncResponse:
        self.calls.append((args, kwargs))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.hermetic
async def test_async_http_adapter_success_close_and_safe_failures(monkeypatch) -> None:
    fake = AsyncClient(AsyncResponse([b"{}"]))
    client_options: list[dict[str, object]] = []

    def client_factory(**kwargs: object) -> AsyncClient:
        client_options.append(kwargs)
        return fake

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    transport = AsyncHttpTransport("https://api.runacode.io")
    assert (await transport(request(), context())).body == b"{}"
    assert len(client_options) == 1
    options = client_options[0]
    assert options["base_url"] == "https://api.runacode.io"
    assert options["follow_redirects"] is False
    assert options["trust_env"] is False
    tls = options["verify"]
    assert isinstance(tls, ssl.SSLContext)
    assert tls.minimum_version is ssl.TLSVersion.TLSv1_2
    assert tls.check_hostname is True
    assert tls.verify_mode is ssl.CERT_REQUIRED
    assert fake.calls[0][0][:2] == ("GET", "/v1/sessions")
    assert fake.calls[0][1]["follow_redirects"] is False
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

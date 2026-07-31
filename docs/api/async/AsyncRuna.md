# `AsyncRuna`

Asynchronous root client.

## Import

`from runa import AsyncRuna`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AsyncRuna(*, api_key: str | None = None, base_url: str | None = None, config_file: str | os.PathLike[str] | None = None, diagnostic_sink: object | None = None, trace_sink: object | None = None)`

## Artifact docstring

Asynchronous root client.

Args:
    api_key: Explicit API key, otherwise resolved from accepted configuration.
    base_url: HTTPS service origin override.
    config_file: Explicit configuration file path.
    diagnostic_sink: Optional disclosure-safe diagnostic sink.
    trace_sink: Optional disclosure-safe trace sink.
Raises:
    ConfigError: If effective configuration is invalid.
Examples:
    See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`sessions`](#sessions) | `AsyncSessionsManager` | Return the stable asynchronous sessions manager. | `AsyncSessionsManager` | None |

<a id="sessions"></a>
### `sessions`

Return the stable asynchronous sessions manager.

- Exact shape: `AsyncSessionsManager`
- Returns: `AsyncSessionsManager`
- Raises: None

Return the stable asynchronous sessions manager.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.

| [`records`](#records) | `AsyncRecordsManager` | Return the stable asynchronous records manager. | `AsyncRecordsManager` | None |

<a id="records"></a>
### `records`

Return the stable asynchronous records manager.

- Exact shape: `AsyncRecordsManager`
- Returns: `AsyncRecordsManager`
- Raises: None

Return the stable asynchronous records manager.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.

| [`me`](#me) | `me() -> Me` | Read the authenticated account asynchronously. | `Me` | `ApiError`, `CancelledError` |

<a id="me"></a>
### `me`

Read the authenticated account asynchronously.

- Exact shape: `me() -> Me`
- Returns: `Me`
- Raises: `ApiError`, `CancelledError`

Read the authenticated account asynchronously.

Returns:
    Account identity and workspace assignment.
Raises:
    ApiError: If the request fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.

| [`close`](#close) | `close() -> None` | Close client-owned resources asynchronously. | `None` | `CancelledError` |

<a id="close"></a>
### `close`

Close client-owned resources asynchronously.

- Exact shape: `close() -> None`
- Returns: `None`
- Raises: `CancelledError`

Close client-owned resources asynchronously.

Returns:
    ``None`` after all admitted operations and owned transport close.
Raises:
    asyncio.CancelledError: If cancellation interrupts an active close leader.
Examples:
    See ``REF-EX-ASYNCRUNA`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`Runa`](../sync/Runa.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ASYNCRUNA` · `TC-091-09`

```python
async def async_runa(client: AsyncRuna) -> None:
    account = await client.me()
    sessions = client.sessions
    records = client.records
    del account, sessions, records
```

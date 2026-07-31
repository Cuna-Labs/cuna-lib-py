# `AsyncRuna`

Asynchronous root client for an authenticated Runa workspace.

## Import

`from runa import AsyncRuna`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AsyncRuna(*, api_key: str | None = None, base_url: str | None = None, config_file: str | os.PathLike[str] | None = None, diagnostic_sink: object | None = None, trace_sink: object | None = None)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`sessions`](#sessions) | `AsyncSessionsManager` | Stable manager owned by this client. | `AsyncSessionsManager` | None |

<a id="sessions"></a>
### `sessions`

Stable manager owned by this client.

- Exact shape: `AsyncSessionsManager`
- Returns: `AsyncSessionsManager`
- Raises: None

| [`records`](#records) | `AsyncRecordsManager` | Stable manager owned by this client. | `AsyncRecordsManager` | None |

<a id="records"></a>
### `records`

Stable manager owned by this client.

- Exact shape: `AsyncRecordsManager`
- Returns: `AsyncRecordsManager`
- Raises: None

| [`me`](#me) | `me() -> Me` | Read the authenticated account and workspace state. | `Me` | `ApiError`, `CancelledError` |

<a id="me"></a>
### `me`

Read the authenticated account and workspace state.

- Exact shape: `me() -> Me`
- Returns: `Me`
- Raises: `ApiError`, `CancelledError`

| [`close`](#close) | `close() -> None` | Close client-owned transport resources; repeated calls are safe. | `None` | None |

<a id="close"></a>
### `close`

Close client-owned transport resources; repeated calls are safe.

- Exact shape: `close() -> None`
- Returns: `None`
- Raises: None

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

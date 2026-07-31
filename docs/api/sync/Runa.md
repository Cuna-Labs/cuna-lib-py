# `Runa`

Synchronous root client for an authenticated Runa workspace.

## Import

`from runa import Runa`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Runa(*, api_key: str | None = None, base_url: str | None = None, config_file: str | os.PathLike[str] | None = None, transport: SyncTransport | None = None, diagnostic_sink: object | None = None, trace_sink: object | None = None)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`sessions`](#sessions) | `SessionsManager` | Stable manager owned by this client. | `SessionsManager` | None |

<a id="sessions"></a>
### `sessions`

Stable manager owned by this client.

- Exact shape: `SessionsManager`
- Returns: `SessionsManager`
- Raises: None

| [`records`](#records) | `RecordsManager` | Stable manager owned by this client. | `RecordsManager` | None |

<a id="records"></a>
### `records`

Stable manager owned by this client.

- Exact shape: `RecordsManager`
- Returns: `RecordsManager`
- Raises: None

| [`me`](#me) | `me() -> Me` | Read the authenticated account and workspace state. | `Me` | `ApiError` |

<a id="me"></a>
### `me`

Read the authenticated account and workspace state.

- Exact shape: `me() -> Me`
- Returns: `Me`
- Raises: `ApiError`

| [`close`](#close) | `close() -> None` | Close client-owned transport resources; repeated calls are safe. | `None` | None |

<a id="close"></a>
### `close`

Close client-owned transport resources; repeated calls are safe.

- Exact shape: `close() -> None`
- Returns: `None`
- Raises: None

## Sync/async pair

See the behaviorally equivalent [`AsyncRuna`](../async/AsyncRuna.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-RUNA` · `TC-091-09`

```python
def runa(client: Runa) -> None:
    account = client.me()
    sessions = client.sessions
    records = client.records
    del account, sessions, records
```

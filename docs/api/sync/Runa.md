# `Runa`

Synchronous root client.

## Import

`from runa import Runa`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Runa(*, api_key: str | None = None, base_url: str | None = None, config_file: str | os.PathLike[str] | None = None, transport: SyncTransport | None = None, diagnostic_sink: object | None = None, trace_sink: object | None = None)`

## Artifact docstring

Synchronous root client.

Args:
    api_key: Explicit API key, otherwise resolved from accepted configuration.
    base_url: Optional explicit Runa API origin; only ``https://api.runacode.io`` is valid.
    config_file: Explicit configuration file path.
    transport: Advanced synchronous transport override.
    diagnostic_sink: Optional disclosure-safe diagnostic sink.
    trace_sink: Optional disclosure-safe trace sink.
Raises:
    ConfigError: If effective configuration is invalid.
Examples:
    See ``REF-EX-RUNA`` and ``TC-091-09``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`sessions`](#sessions) | `SessionsManager` | Return the stable sessions manager. | `SessionsManager` | None |

<a id="sessions"></a>
### `sessions`

Return the stable sessions manager.

- Exact shape: `SessionsManager`
- Returns: `SessionsManager`
- Raises: None

Return the stable sessions manager.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-RUNA`` and ``TC-091-09``.

| [`records`](#records) | `RecordsManager` | Return the stable records manager. | `RecordsManager` | None |

<a id="records"></a>
### `records`

Return the stable records manager.

- Exact shape: `RecordsManager`
- Returns: `RecordsManager`
- Raises: None

Return the stable records manager.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-RUNA`` and ``TC-091-09``.

| [`me`](#me) | `me() -> Me` | Read the authenticated account. | `Me` | `ApiError` |

<a id="me"></a>
### `me`

Read the authenticated account.

- Exact shape: `me() -> Me`
- Returns: `Me`
- Raises: `ApiError`

Read the authenticated account.

Returns:
    Account identity and workspace assignment.
Raises:
    ApiError: If the request fails or the response is malformed.
Examples:
    See ``REF-EX-RUNA`` and ``TC-091-09``.

| [`close`](#close) | `close() -> None` | Close client-owned resources. | `None` | None |

<a id="close"></a>
### `close`

Close client-owned resources.

- Exact shape: `close() -> None`
- Returns: `None`
- Raises: None

Close client-owned resources.

Returns:
    ``None`` after all admitted operations and owned transport close.
Examples:
    See ``REF-EX-RUNA`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`AsyncRuna`](../async/AsyncRuna.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-RUNA`; `TC-091-09`

```python
def runa(client: Runa) -> None:
    account = client.me()
    sessions = client.sessions
    records = client.records
    del account, sessions, records
```

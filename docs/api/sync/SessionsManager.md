# `SessionsManager`

Stable synchronous session manager obtained from ``Runa.sessions``.

## Import

`from runa import SessionsManager`

## Acquisition

Obtain this stable instance from `Runa.sessions`.

## Signature

`SessionsManager(client: Runa, token: object = None)`

## Artifact docstring

Stable synchronous session manager obtained from ``Runa.sessions``.

Direct construction is unsupported and raises ``TypeError``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`create`](#create) | `create(name: str, options: SessionCreateOptions) -> Session` | Create one session. | `Session` | `ConfigError`, `ApiError` |

<a id="create"></a>
### `create`

Create one session.

- Exact shape: `create(name: str, options: SessionCreateOptions) -> Session`
- Returns: `Session`
- Raises: `ConfigError`, `ApiError`

Create one session.

Args:
    name: Human-readable name of 1-80 characters.
    options: Explicit omission-aware creation options.
Returns:
    A client-owned session handle.
Raises:
    ConfigError: If an input violates the local contract.
    ApiError: If the request fails or the response is malformed.
Examples:
    See ``REF-EX-SESSIONSMANAGER`` and ``TC-091-09``.

| [`list`](#list) | `list() -> list[Session]` | List visible sessions. | `list[Session]` | `ApiError` |

<a id="list"></a>
### `list`

List visible sessions.

- Exact shape: `list() -> list[Session]`
- Returns: `list[Session]`
- Raises: `ApiError`

List visible sessions.

Returns:
    New client-owned handles in service order.
Raises:
    ApiError: If the request fails or the response is malformed.
Examples:
    See ``REF-EX-SESSIONSMANAGER`` and ``TC-091-09``.

| [`get`](#get) | `get(session_id: str) -> Session` | Retrieve one session. | `Session` | `ConfigError`, `ApiError` |

<a id="get"></a>
### `get`

Retrieve one session.

- Exact shape: `get(session_id: str) -> Session`
- Returns: `Session`
- Raises: `ConfigError`, `ApiError`

Retrieve one session.

Args:
    session_id: Canonical lowercase session UUID.
Returns:
    A client-owned handle whose ID matches ``session_id``.
Raises:
    ConfigError: If ``session_id`` is not canonical.
    ApiError: If the request fails, is missing, or is malformed.
Examples:
    See ``REF-EX-SESSIONSMANAGER`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`AsyncSessionsManager`](../async/AsyncSessionsManager.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-SESSIONSMANAGER` · `TC-091-09`

```python
def sessions_manager(manager: SessionsManager, options: SessionCreateOptions) -> None:
    created = manager.create("reference", options)
    listed = manager.list()
    loaded = manager.get(created.id)
    del listed, loaded
```

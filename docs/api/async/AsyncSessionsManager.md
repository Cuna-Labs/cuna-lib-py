# `AsyncSessionsManager`

Stable asynchronous session manager obtained from ``AsyncCuna.sessions``.

## Import

`from cuna import AsyncSessionsManager`

## Acquisition

Obtain this stable instance from `AsyncCuna.sessions`.

## Signature

`AsyncSessionsManager(client: AsyncCuna, token: object = None)`

## Artifact docstring

Stable asynchronous session manager obtained from ``AsyncCuna.sessions``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`create`](#create) | `create(name: str, options: SessionCreateOptions) -> AsyncSession` | Create one session asynchronously. | `AsyncSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="create"></a>
### `create`

Create one session asynchronously.

- Exact shape: `create(name: str, options: SessionCreateOptions) -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Create one session asynchronously.

Args:
    name: Human-readable name of 1-80 characters.
    options: Explicit omission-aware creation options.
Returns:
    A client-owned asynchronous session handle.
Raises:
    ConfigError: If an input violates the local contract.
    ApiError: If the request fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSIONSMANAGER`` and ``TC-091-09``.

| [`list`](#list) | `list() -> list[AsyncSession]` | List visible sessions asynchronously. | `list[AsyncSession]` | `ApiError`, `CancelledError` |

<a id="list"></a>
### `list`

List visible sessions asynchronously.

- Exact shape: `list() -> list[AsyncSession]`
- Returns: `list[AsyncSession]`
- Raises: `ApiError`, `CancelledError`

List visible sessions asynchronously.

Returns:
    New client-owned asynchronous handles in service order.
Raises:
    ApiError: If the request fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSIONSMANAGER`` and ``TC-091-09``.

| [`get`](#get) | `get(session_id: str) -> AsyncSession` | Retrieve one session asynchronously. | `AsyncSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="get"></a>
### `get`

Retrieve one session asynchronously.

- Exact shape: `get(session_id: str) -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Retrieve one session asynchronously.

Args:
    session_id: Canonical lowercase session UUID.
Returns:
    A client-owned handle whose ID matches ``session_id``.
Raises:
    ConfigError: If ``session_id`` is not canonical.
    ApiError: If the request fails, is missing, or is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCSESSIONSMANAGER`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`SessionsManager`](../sync/SessionsManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCSESSIONSMANAGER`; `TC-091-09`

```python
async def async_sessions_manager(
    manager: AsyncSessionsManager, options: SessionCreateOptions
) -> None:
    created = await manager.create("reference", options)
    listed = await manager.list()
    loaded = await manager.get(created.id)
    del listed, loaded
```

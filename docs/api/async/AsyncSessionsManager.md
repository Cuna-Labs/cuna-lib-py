# `AsyncSessionsManager`

Asynchronous entry point for creating, listing, and retrieving sessions.

## Import

`from runa import AsyncSessionsManager`

## Acquisition

Obtain this stable instance from `AsyncRuna.sessions`.

## Signature

`AsyncSessionsManager(client: AsyncRuna, token: object = None)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`create`](#create) | `create(name: str, options: SessionCreateOptions) -> AsyncSession` | Create one session from a 1-80 character name and explicit options. | `AsyncSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="create"></a>
### `create`

Create one session from a 1-80 character name and explicit options.

- Exact shape: `create(name: str, options: SessionCreateOptions) -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

| [`list`](#list) | `list() -> list[AsyncSession]` | List the resources visible to the authenticated workspace. | `list[AsyncSession]` | `ApiError`, `CancelledError` |

<a id="list"></a>
### `list`

List the resources visible to the authenticated workspace.

- Exact shape: `list() -> list[AsyncSession]`
- Returns: `list[AsyncSession]`
- Raises: `ApiError`, `CancelledError`

| [`get`](#get) | `get(session_id: str) -> AsyncSession` | Retrieve one session by canonical UUID. | `AsyncSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="get"></a>
### `get`

Retrieve one session by canonical UUID.

- Exact shape: `get(session_id: str) -> AsyncSession`
- Returns: `AsyncSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

## Sync/async pair

See the behaviorally equivalent [`SessionsManager`](../sync/SessionsManager.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ASYNCSESSIONSMANAGER` · `TC-091-09`

```python
async def async_sessions_manager(
    manager: AsyncSessionsManager, options: SessionCreateOptions
) -> None:
    created = await manager.create("reference", options)
    listed = await manager.list()
    loaded = await manager.get(created.id)
    del listed, loaded
```

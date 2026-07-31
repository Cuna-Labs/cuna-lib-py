# `SessionsManager`

Synchronous entry point for creating, listing, and retrieving sessions.

## Import

`from runa import SessionsManager`

## Acquisition

Obtain this stable instance from `Runa.sessions`.

## Signature

`SessionsManager(client: Runa, token: object = None)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`create`](#create) | `create(name: str, options: SessionCreateOptions) -> Session` | Create one session from a 1-80 character name and explicit options. | `Session` | `ConfigError`, `ApiError` |

<a id="create"></a>
### `create`

Create one session from a 1-80 character name and explicit options.

- Exact shape: `create(name: str, options: SessionCreateOptions) -> Session`
- Returns: `Session`
- Raises: `ConfigError`, `ApiError`

| [`list`](#list) | `list() -> list[Session]` | List the resources visible to the authenticated workspace. | `list[Session]` | `ApiError` |

<a id="list"></a>
### `list`

List the resources visible to the authenticated workspace.

- Exact shape: `list() -> list[Session]`
- Returns: `list[Session]`
- Raises: `ApiError`

| [`get`](#get) | `get(session_id: str) -> Session` | Retrieve one session by canonical UUID. | `Session` | `ConfigError`, `ApiError` |

<a id="get"></a>
### `get`

Retrieve one session by canonical UUID.

- Exact shape: `get(session_id: str) -> Session`
- Returns: `Session`
- Raises: `ConfigError`, `ApiError`

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

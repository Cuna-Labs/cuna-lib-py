# `AsyncAgentSessionsManager`

Stable asynchronous manager for AgentSession process resources.

## Import

`from cuna import AsyncAgentSessionsManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AsyncAgentSessionsManager(client: AsyncCuna, token: object = None)`

## Artifact docstring

Stable asynchronous manager for AgentSession process resources.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`list`](#list) | `list(machine_id: str, options: AgentSessionListOptions | None = None) -> AgentSessionPage` | Return one bounded AgentSession page asynchronously. | `AgentSessionPage` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="list"></a>
### `list`

Return one bounded AgentSession page asynchronously.

- Exact shape: `list(machine_id: str, options: AgentSessionListOptions | None = None) -> AgentSessionPage`
- Returns: `AgentSessionPage`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Return one bounded AgentSession page asynchronously.

| [`create`](#create) | `create(machine_id: str, options: AgentSessionCreateOptions) -> AgentSession` | Create one durable AgentSession launch intent asynchronously. | `AgentSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="create"></a>
### `create`

Create one durable AgentSession launch intent asynchronously.

- Exact shape: `create(machine_id: str, options: AgentSessionCreateOptions) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Create one durable AgentSession launch intent asynchronously.

| [`get`](#get) | `get(agent_session_id: str) -> AgentSession` | Get one AgentSession asynchronously. | `AgentSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="get"></a>
### `get`

Get one AgentSession asynchronously.

- Exact shape: `get(agent_session_id: str) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Get one AgentSession asynchronously.

| [`agent_auth`](#agent_auth) | `agent_auth(agent_session: AgentSession) -> AgentSessionAuth` | Read fresh auth evidence bound to an already admitted AgentSession. | `AgentSessionAuth` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="agent_auth"></a>
### `agent_auth`

Read fresh auth evidence bound to an already admitted AgentSession.

- Exact shape: `agent_auth(agent_session: AgentSession) -> AgentSessionAuth`
- Returns: `AgentSessionAuth`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Read fresh auth evidence bound to an already admitted AgentSession.

| [`rename`](#rename) | `rename(agent_session_id: str, name: str) -> AgentSession` | Rename AgentSession metadata asynchronously. | `AgentSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="rename"></a>
### `rename`

Rename AgentSession metadata asynchronously.

- Exact shape: `rename(agent_session_id: str, name: str) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Rename AgentSession metadata asynchronously.

| [`terminate`](#terminate) | `terminate(agent_session_id: str) -> AgentSession` | Request durable termination asynchronously. | `AgentSession` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="terminate"></a>
### `terminate`

Request durable termination asynchronously.

- Exact shape: `terminate(agent_session_id: str) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Request durable termination asynchronously.

| [`create_terminal_connection`](#create_terminal_connection) | `create_terminal_connection(agent_session_id: str, options: TerminalConnectionCreateOptions) -> TerminalConnectionGrant` | Create terminal connection metadata without opening or consuming the stream. | `TerminalConnectionGrant` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="create_terminal_connection"></a>
### `create_terminal_connection`

Create terminal connection metadata without opening or consuming the stream.

- Exact shape: `create_terminal_connection(agent_session_id: str, options: TerminalConnectionCreateOptions) -> TerminalConnectionGrant`
- Returns: `TerminalConnectionGrant`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Create terminal connection metadata without opening or consuming the stream.

## Sync/async pair

See the behaviorally equivalent [`AgentSessionsManager`](../sync/AgentSessionsManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCAGENTSESSIONSMANAGER`; `TC-091-09`

```python
async def async_agent_sessions_manager(manager: AsyncAgentSessionsManager) -> None:
    session = await manager.get("22222222-2222-4222-8222-222222222222")
    authentication = await manager.agent_auth(session)
    del authentication
```

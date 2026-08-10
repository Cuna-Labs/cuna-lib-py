# `AgentSessionsManager`

Stable synchronous manager for processes owned by one Runa machine.

## Import

`from runa import AgentSessionsManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AgentSessionsManager(client: Runa, token: object = None)`

## Artifact docstring

Stable synchronous manager for processes owned by one Runa machine.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`list`](#list) | `list(machine_id: str, options: AgentSessionListOptions | None = None) -> AgentSessionPage` | Return one bounded page for an owned machine. | `AgentSessionPage` | `ConfigError`, `ApiError` |

<a id="list"></a>
### `list`

Return one bounded page for an owned machine.

- Exact shape: `list(machine_id: str, options: AgentSessionListOptions | None = None) -> AgentSessionPage`
- Returns: `AgentSessionPage`
- Raises: `ConfigError`, `ApiError`

Return one bounded page for an owned machine.

| [`create`](#create) | `create(machine_id: str, options: AgentSessionCreateOptions) -> AgentSession` | Create one durable AgentSession launch intent. | `AgentSession` | `ConfigError`, `ApiError` |

<a id="create"></a>
### `create`

Create one durable AgentSession launch intent.

- Exact shape: `create(machine_id: str, options: AgentSessionCreateOptions) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`

Create one durable AgentSession launch intent.

| [`get`](#get) | `get(agent_session_id: str) -> AgentSession` | Get one AgentSession by its opaque canonical UUID. | `AgentSession` | `ConfigError`, `ApiError` |

<a id="get"></a>
### `get`

Get one AgentSession by its opaque canonical UUID.

- Exact shape: `get(agent_session_id: str) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`

Get one AgentSession by its opaque canonical UUID.

| [`agent_auth`](#agent_auth) | `agent_auth(agent_session: AgentSession) -> AgentSessionAuth` | Read fresh auth evidence bound to an already admitted AgentSession. | `AgentSessionAuth` | `ConfigError`, `ApiError` |

<a id="agent_auth"></a>
### `agent_auth`

Read fresh auth evidence bound to an already admitted AgentSession.

- Exact shape: `agent_auth(agent_session: AgentSession) -> AgentSessionAuth`
- Returns: `AgentSessionAuth`
- Raises: `ConfigError`, `ApiError`

Read fresh auth evidence bound to an already admitted AgentSession.

| [`rename`](#rename) | `rename(agent_session_id: str, name: str) -> AgentSession` | Rename metadata without changing process facts. | `AgentSession` | `ConfigError`, `ApiError` |

<a id="rename"></a>
### `rename`

Rename metadata without changing process facts.

- Exact shape: `rename(agent_session_id: str, name: str) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`

Rename metadata without changing process facts.

| [`terminate`](#terminate) | `terminate(agent_session_id: str) -> AgentSession` | Request durable termination without asserting process absence. | `AgentSession` | `ConfigError`, `ApiError` |

<a id="terminate"></a>
### `terminate`

Request durable termination without asserting process absence.

- Exact shape: `terminate(agent_session_id: str) -> AgentSession`
- Returns: `AgentSession`
- Raises: `ConfigError`, `ApiError`

Request durable termination without asserting process absence.

| [`create_terminal_connection`](#create_terminal_connection) | `create_terminal_connection(agent_session_id: str, options: TerminalConnectionCreateOptions) -> TerminalConnectionGrant` | Create terminal connection metadata without opening or consuming the stream. | `TerminalConnectionGrant` | `ConfigError`, `ApiError` |

<a id="create_terminal_connection"></a>
### `create_terminal_connection`

Create terminal connection metadata without opening or consuming the stream.

- Exact shape: `create_terminal_connection(agent_session_id: str, options: TerminalConnectionCreateOptions) -> TerminalConnectionGrant`
- Returns: `TerminalConnectionGrant`
- Raises: `ConfigError`, `ApiError`

Create terminal connection metadata without opening or consuming the stream.

## Sync/async pair

See the behaviorally equivalent [`AsyncAgentSessionsManager`](../async/AsyncAgentSessionsManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONSMANAGER`; `TC-091-09`

```python
def agent_sessions_manager(manager: AgentSessionsManager) -> None:
    session = manager.get("22222222-2222-4222-8222-222222222222")
    authentication = manager.agent_auth(session)
    del authentication
```

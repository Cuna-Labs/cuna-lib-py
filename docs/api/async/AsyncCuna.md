# `AsyncCuna`

Asynchronous root client.

## Import

`from cuna import AsyncCuna`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AsyncCuna(*, api_key: str | None = None, base_url: str | None = None, config_file: str | os.PathLike[str] | None = None, diagnostic_sink: object | None = None, trace_sink: object | None = None)`

## Artifact docstring

Asynchronous root client.

Args:
    api_key: Explicit API key, otherwise resolved from accepted configuration.
    base_url: Optional explicit Cuna API origin. ``https://api.getcuna.com`` is canonical;
        ``https://api.runacode.io`` remains accepted for compatibility.
    config_file: Explicit configuration file path.
    diagnostic_sink: Optional disclosure-safe diagnostic sink.
    trace_sink: Optional disclosure-safe trace sink.
Raises:
    ConfigError: If effective configuration is invalid.
Examples:
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

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
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

| [`agent_sessions`](#agent_sessions) | `AsyncAgentSessionsManager` | Return the stable asynchronous AgentSession manager. | `AsyncAgentSessionsManager` | None |

<a id="agent_sessions"></a>
### `agent_sessions`

Return the stable asynchronous AgentSession manager.

- Exact shape: `AsyncAgentSessionsManager`
- Returns: `AsyncAgentSessionsManager`
- Raises: None

Return the stable asynchronous AgentSession manager.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

| [`capabilities`](#capabilities) | `AsyncCapabilitiesManager` | Return the stable asynchronous capability discovery manager. | `AsyncCapabilitiesManager` | None |

<a id="capabilities"></a>
### `capabilities`

Return the stable asynchronous capability discovery manager.

- Exact shape: `AsyncCapabilitiesManager`
- Returns: `AsyncCapabilitiesManager`
- Raises: None

Return the stable asynchronous capability discovery manager.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

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
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

| [`workspace_sync`](#workspace_sync) | `AsyncWorkspaceSyncManager` | Return the stable asynchronous workspace synchronization manager. | `AsyncWorkspaceSyncManager` | None |

<a id="workspace_sync"></a>
### `workspace_sync`

Return the stable asynchronous workspace synchronization manager.

- Exact shape: `AsyncWorkspaceSyncManager`
- Returns: `AsyncWorkspaceSyncManager`
- Raises: None

Return the stable asynchronous workspace synchronization manager.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

| [`workspace_bindings`](#workspace_bindings) | `AsyncWorkspaceBindingsManager` | Return asynchronous canonical workspace binding operations. | `AsyncWorkspaceBindingsManager` | None |

<a id="workspace_bindings"></a>
### `workspace_bindings`

Return asynchronous canonical workspace binding operations.

- Exact shape: `AsyncWorkspaceBindingsManager`
- Returns: `AsyncWorkspaceBindingsManager`
- Raises: None

Return asynchronous canonical workspace binding operations.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

| [`machine_creates`](#machine_creates) | `AsyncMachineCreatesManager` | Return asynchronous machine-create recovery operations. | `AsyncMachineCreatesManager` | None |

<a id="machine_creates"></a>
### `machine_creates`

Return asynchronous machine-create recovery operations.

- Exact shape: `AsyncMachineCreatesManager`
- Returns: `AsyncMachineCreatesManager`
- Raises: None

Return asynchronous machine-create recovery operations.

Returns:
    The manager owned by this client.
Examples:
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

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
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

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
    See ``REF-EX-ASYNCCUNA`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`Cuna`](../sync/Cuna.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCCUNA`; `TC-091-09`

```python
async def async_cuna(client: AsyncCuna) -> None:
    account = await client.me()
    sessions = client.sessions
    records = client.records
    capabilities = client.capabilities
    del account, sessions, records, capabilities
```

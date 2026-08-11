# `AsyncWorkspaceBindingsManager`

Asynchronous canonical workspace binding operations.

## Import

`from cuna import AsyncWorkspaceBindingsManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AsyncWorkspaceBindingsManager(client: AsyncCuna, token: object = None)`

## Artifact docstring

Asynchronous canonical workspace binding operations.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`create`](#create) | `create(request: WorkspaceBindingCreateRequest, idempotency_key: str) -> WorkspaceBinding` | Create or exactly adopt one canonical workspace binding asynchronously. | `WorkspaceBinding` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="create"></a>
### `create`

Create or exactly adopt one canonical workspace binding asynchronously.

- Exact shape: `create(request: WorkspaceBindingCreateRequest, idempotency_key: str) -> WorkspaceBinding`
- Returns: `WorkspaceBinding`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Create or exactly adopt one canonical workspace binding asynchronously.

| [`get`](#get) | `get(binding_id: str, identity: WorkspaceBindingLookup) -> WorkspaceBinding` | Get one canonical binding using its complete identity asynchronously. | `WorkspaceBinding` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="get"></a>
### `get`

Get one canonical binding using its complete identity asynchronously.

- Exact shape: `get(binding_id: str, identity: WorkspaceBindingLookup) -> WorkspaceBinding`
- Returns: `WorkspaceBinding`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Get one canonical binding using its complete identity asynchronously.

## Sync/async pair

See the behaviorally equivalent [`WorkspaceBindingsManager`](../sync/WorkspaceBindingsManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCWORKSPACEBINDINGSMANAGER`; `TC-091-09`

```python
async def async_workspace_bindings_manager(manager: AsyncWorkspaceBindingsManager) -> None:
    del manager
```

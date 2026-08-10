# `WorkspaceBindingsManager`

Create, adopt, and resolve canonical workspace bindings.

## Import

`from runa import WorkspaceBindingsManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceBindingsManager(client: Runa, token: object = None)`

## Artifact docstring

Create, adopt, and resolve canonical workspace bindings.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`create`](#create) | `create(request: WorkspaceBindingCreateRequest, idempotency_key: str) -> WorkspaceBinding` | Create or exactly adopt one canonical workspace binding. | `WorkspaceBinding` | `ConfigError`, `ApiError` |

<a id="create"></a>
### `create`

Create or exactly adopt one canonical workspace binding.

- Exact shape: `create(request: WorkspaceBindingCreateRequest, idempotency_key: str) -> WorkspaceBinding`
- Returns: `WorkspaceBinding`
- Raises: `ConfigError`, `ApiError`

Create or exactly adopt one canonical workspace binding.

| [`get`](#get) | `get(binding_id: str, identity: WorkspaceBindingLookup) -> WorkspaceBinding` | Get one canonical binding using its complete authenticated identity. | `WorkspaceBinding` | `ConfigError`, `ApiError` |

<a id="get"></a>
### `get`

Get one canonical binding using its complete authenticated identity.

- Exact shape: `get(binding_id: str, identity: WorkspaceBindingLookup) -> WorkspaceBinding`
- Returns: `WorkspaceBinding`
- Raises: `ConfigError`, `ApiError`

Get one canonical binding using its complete authenticated identity.

## Sync/async pair

See the behaviorally equivalent [`AsyncWorkspaceBindingsManager`](../async/AsyncWorkspaceBindingsManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACEBINDINGSMANAGER`; `TC-091-09`

```python
def workspace_bindings_manager(manager: WorkspaceBindingsManager) -> None:
    del manager
```

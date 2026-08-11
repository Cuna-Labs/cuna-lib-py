# `AsyncMachineCreatesManager`

Asynchronous machine-create status and exact-name reconciliation.

## Import

`from cuna import AsyncMachineCreatesManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AsyncMachineCreatesManager(client: AsyncCuna, token: object = None)`

## Artifact docstring

Asynchronous machine-create status and exact-name reconciliation.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`get`](#get) | `get(request_id: str) -> MachineCreateRequest` | Get one non-secret machine-create request state asynchronously. | `MachineCreateRequest` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="get"></a>
### `get`

Get one non-secret machine-create request state asynchronously.

- Exact shape: `get(request_id: str) -> MachineCreateRequest`
- Returns: `MachineCreateRequest`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Get one non-secret machine-create request state asynchronously.

| [`reconcile`](#reconcile) | `reconcile(request_id: str) -> MachineCreateRequest` | Reconcile one exact machine-create request state asynchronously. | `MachineCreateRequest` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="reconcile"></a>
### `reconcile`

Reconcile one exact machine-create request state asynchronously.

- Exact shape: `reconcile(request_id: str) -> MachineCreateRequest`
- Returns: `MachineCreateRequest`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Reconcile one exact machine-create request state asynchronously.

## Sync/async pair

See the behaviorally equivalent [`MachineCreatesManager`](../sync/MachineCreatesManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCMACHINECREATESMANAGER`; `TC-091-09`

```python
async def async_machine_creates_manager(manager: AsyncMachineCreatesManager) -> None:
    del manager
```

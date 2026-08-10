# `MachineCreatesManager`

Non-secret machine-create status and exact-name reconciliation.

## Import

`from runa import MachineCreatesManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`MachineCreatesManager(client: Runa, token: object = None)`

## Artifact docstring

Non-secret machine-create status and exact-name reconciliation.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`get`](#get) | `get(request_id: str) -> MachineCreateRequest` | Get one non-secret machine-create request state. | `MachineCreateRequest` | `ConfigError`, `ApiError` |

<a id="get"></a>
### `get`

Get one non-secret machine-create request state.

- Exact shape: `get(request_id: str) -> MachineCreateRequest`
- Returns: `MachineCreateRequest`
- Raises: `ConfigError`, `ApiError`

Get one non-secret machine-create request state.

| [`reconcile`](#reconcile) | `reconcile(request_id: str) -> MachineCreateRequest` | Reconcile one exact machine-create request state. | `MachineCreateRequest` | `ConfigError`, `ApiError` |

<a id="reconcile"></a>
### `reconcile`

Reconcile one exact machine-create request state.

- Exact shape: `reconcile(request_id: str) -> MachineCreateRequest`
- Returns: `MachineCreateRequest`
- Raises: `ConfigError`, `ApiError`

Reconcile one exact machine-create request state.

## Sync/async pair

See the behaviorally equivalent [`AsyncMachineCreatesManager`](../async/AsyncMachineCreatesManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-MACHINECREATESMANAGER`; `TC-091-09`

```python
def machine_creates_manager(manager: MachineCreatesManager) -> None:
    del manager
```

# `MachineCreateRequest`

Non-secret machine creation status and recovery action.

## Import

`from cuna import MachineCreateRequest`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`MachineCreateRequest(id: str, machine_id: str, state: Literal['prepared', 'in_progress', 'unknown', 'provider_succeeded', 'settled', 'terminal_failed'], retryable: bool, action: Literal['retry_create', 'reconcile', 'wait', 'none'], updated_at: str)`

## Artifact docstring

Non-secret machine creation status and recovery action.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `id` | `str` | Canonical identifier. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `state` | `Literal['prepared', 'in_progress', 'unknown', 'provider_succeeded', 'settled', 'terminal_failed']` | Strict secret-free authentication state of the session agent. |
| `retryable` | `bool` | Accepted `retryable` value defined by the public contract. |
| `action` | `Literal['retry_create', 'reconcile', 'wait', 'none']` | Accepted `action` value defined by the public contract. |
| `updated_at` | `str` | Service timestamp encoded as an RFC 3339 string. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-MACHINECREATEREQUEST`; `TC-091-09`

```python
def machine_create_request(value: MachineCreateRequest) -> str:
    return value.state
```

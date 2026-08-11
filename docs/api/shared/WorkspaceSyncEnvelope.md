# `WorkspaceSyncEnvelope`

Protocol and capability evidence wrapping workspace synchronization data.

## Import

`from cuna import WorkspaceSyncEnvelope`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncEnvelope(request_id: str, selected_protocol: Literal[1, 2], capabilities: tuple[WorkspaceSyncCapability, ...], data: WorkspaceSyncData)`

## Artifact docstring

Protocol and capability evidence wrapping workspace synchronization data.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `request_id` | `str` | Accepted `request_id` value defined by the public contract. |
| `selected_protocol` | `Literal[1, 2]` | Accepted `selected_protocol` value defined by the public contract. |
| `capabilities` | `tuple[WorkspaceSyncCapability, ...]` | Ordered capability descriptions. |
| `data` | `WorkspaceSyncData` | Accepted `data` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCENVELOPE`; `TC-091-09`

```python
def workspace_sync_envelope(value: WorkspaceSyncEnvelope[WorkspaceSyncSession]) -> str:
    return value.request_id
```

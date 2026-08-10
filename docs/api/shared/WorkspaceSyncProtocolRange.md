# `WorkspaceSyncProtocolRange`

Inclusive workspace synchronization protocol range.

## Import

`from runa import WorkspaceSyncProtocolRange`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncProtocolRange(minimum: int, maximum: int)`

## Artifact docstring

Inclusive workspace synchronization protocol range.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `minimum` | `int` | Accepted `minimum` value defined by the public contract. |
| `maximum` | `int` | Accepted `maximum` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCPROTOCOLRANGE`; `TC-091-09`

```python
def workspace_sync_protocol_range(value: WorkspaceSyncProtocolRange) -> int:
    return value.maximum
```

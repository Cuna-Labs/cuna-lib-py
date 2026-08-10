# `WorkspaceSyncBeginRequest`

Authority-bound request to begin workspace synchronization.

## Import

`from cuna import WorkspaceSyncBeginRequest`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncBeginRequest(workspace_binding_id: str, machine_id: str, base_generation: int, exclusion_policy_digest: str, protocol: WorkspaceSyncProtocolRange, minimum_reader: int, minimum_writer: int)`

## Artifact docstring

Authority-bound request to begin workspace synchronization.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `workspace_binding_id` | `str` | Accepted `workspace_binding_id` value defined by the public contract. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `base_generation` | `int` | Accepted `base_generation` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |
| `protocol` | `WorkspaceSyncProtocolRange` | Accepted `protocol` value defined by the public contract. |
| `minimum_reader` | `int` | Accepted `minimum_reader` value defined by the public contract. |
| `minimum_writer` | `int` | Accepted `minimum_writer` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCBEGINREQUEST`; `TC-091-09`

```python
def workspace_sync_begin_request(value: WorkspaceSyncBeginRequest) -> str:
    return value.workspace_binding_id
```

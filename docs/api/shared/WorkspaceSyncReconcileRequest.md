# `WorkspaceSyncReconcileRequest`

Request to reconcile local and committed workspace state.

## Import

`from cuna import WorkspaceSyncReconcileRequest`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncReconcileRequest(workspace_binding_id: str, machine_id: str, observed_generation: int, exclusion_policy_digest: str, manifest_root: str, protocol: WorkspaceSyncProtocolRange)`

## Artifact docstring

Request to reconcile local and committed workspace state.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `workspace_binding_id` | `str` | Accepted `workspace_binding_id` value defined by the public contract. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `observed_generation` | `int` | Accepted `observed_generation` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |
| `manifest_root` | `str` | Accepted `manifest_root` value defined by the public contract. |
| `protocol` | `WorkspaceSyncProtocolRange` | Accepted `protocol` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCRECONCILEREQUEST`; `TC-091-09`

```python
def workspace_sync_reconcile_request(value: WorkspaceSyncReconcileRequest) -> str:
    return value.workspace_binding_id
```

# `WorkspaceSyncReconcileReceipt`

Receipt describing workspace convergence or required reconciliation.

## Import

`from cuna import WorkspaceSyncReconcileReceipt`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncReconcileReceipt(selected_protocol: Literal[1, 2], status: Literal['converged', 'reconciliation_required'], active_generation: int, active_manifest_root: str, exclusion_policy_digest: str)`

## Artifact docstring

Receipt describing workspace convergence or required reconciliation.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `selected_protocol` | `Literal[1, 2]` | Accepted `selected_protocol` value defined by the public contract. |
| `status` | `Literal['converged', 'reconciliation_required']` | Current lifecycle state. |
| `active_generation` | `int` | Accepted `active_generation` value defined by the public contract. |
| `active_manifest_root` | `str` | Accepted `active_manifest_root` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCRECONCILERECEIPT`; `TC-091-09`

```python
def workspace_sync_reconcile_receipt(value: WorkspaceSyncReconcileReceipt) -> str:
    return value.status
```

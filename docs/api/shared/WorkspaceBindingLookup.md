# `WorkspaceBindingLookup`

Full identity proof required to read a canonical workspace binding.

## Import

`from cuna import WorkspaceBindingLookup`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceBindingLookup(workspace_id: str, project_id: str, local_instance_id: str, machine_id: str, exclusion_policy_digest: str)`

## Artifact docstring

Full identity proof required to read a canonical workspace binding.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `workspace_id` | `str` | Accepted `workspace_id` value defined by the public contract. |
| `project_id` | `str` | Accepted `project_id` value defined by the public contract. |
| `local_instance_id` | `str` | Accepted `local_instance_id` value defined by the public contract. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACEBINDINGLOOKUP`; `TC-091-09`

```python
def workspace_binding_lookup(value: WorkspaceBindingLookup) -> str:
    return value.workspace_id
```

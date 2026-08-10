# `WorkspaceBindingCreateRequest`

Canonical identity tuple used to create or adopt a workspace binding.

## Import

`from cuna import WorkspaceBindingCreateRequest`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceBindingCreateRequest(workspace_id: str, project_id: str, local_instance_id: str, machine_id: str, exclusion_policy_digest: str, excluded_prefixes: list[str])`

## Artifact docstring

Canonical identity tuple used to create or adopt a workspace binding.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `workspace_id` | `str` | Accepted `workspace_id` value defined by the public contract. |
| `project_id` | `str` | Accepted `project_id` value defined by the public contract. |
| `local_instance_id` | `str` | Accepted `local_instance_id` value defined by the public contract. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |
| `excluded_prefixes` | `list[str]` | Accepted `excluded_prefixes` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACEBINDINGCREATEREQUEST`; `TC-091-09`

```python
def workspace_binding_create_request(value: WorkspaceBindingCreateRequest) -> str:
    return value.workspace_id
```

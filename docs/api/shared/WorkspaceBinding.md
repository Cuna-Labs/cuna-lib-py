# `WorkspaceBinding`

Exact authenticated binding between a local project and a Runa machine.

## Import

`from runa import WorkspaceBinding`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceBinding(binding_id: str, workspace_id: str, project_id: str, local_instance_id: str, machine_id: str, remote_root: str, exclusion_policy_digest: str, active_generation: int, active_manifest_root: str, binding_epoch: int, minimum_reader: int, minimum_writer: int, created_at: str, updated_at: str)`

## Artifact docstring

Exact authenticated binding between a local project and a Runa machine.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `binding_id` | `str` | Accepted `binding_id` value defined by the public contract. |
| `workspace_id` | `str` | Accepted `workspace_id` value defined by the public contract. |
| `project_id` | `str` | Accepted `project_id` value defined by the public contract. |
| `local_instance_id` | `str` | Accepted `local_instance_id` value defined by the public contract. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `remote_root` | `str` | Accepted `remote_root` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |
| `active_generation` | `int` | Accepted `active_generation` value defined by the public contract. |
| `active_manifest_root` | `str` | Accepted `active_manifest_root` value defined by the public contract. |
| `binding_epoch` | `int` | Accepted `binding_epoch` value defined by the public contract. |
| `minimum_reader` | `int` | Accepted `minimum_reader` value defined by the public contract. |
| `minimum_writer` | `int` | Accepted `minimum_writer` value defined by the public contract. |
| `created_at` | `str` | Service timestamp encoded as an RFC 3339 string. |
| `updated_at` | `str` | Service timestamp encoded as an RFC 3339 string. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACEBINDING`; `TC-091-09`

```python
def workspace_binding(value: WorkspaceBinding) -> str:
    return value.binding_id
```

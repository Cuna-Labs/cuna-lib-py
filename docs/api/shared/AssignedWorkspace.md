# `AssignedWorkspace`

Assigned workspace state.

## Import

`from cuna import AssignedWorkspace`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AssignedWorkspace(assigned: Literal[True], id: str, usage: EstimatedUsage)`

## Artifact docstring

Assigned workspace state.

Attributes:
    assigned: Literal ``True`` discriminator.
    id: Canonical public workspace UUID used by synchronization APIs.
    usage: Estimated workspace usage.
Examples:
    See ``REF-EX-ASSIGNEDWORKSPACE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `assigned` | `Literal[True]` | Discriminator for the workspace union. |
| `id` | `str` | Canonical identifier. |
| `usage` | `EstimatedUsage` | Estimated usage for an assigned workspace. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASSIGNEDWORKSPACE`; `TC-091-09`

```python
def assigned_workspace(value: AssignedWorkspace) -> EstimatedUsage:
    return value.usage
```

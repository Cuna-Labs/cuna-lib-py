# `AssignedWorkspace`

Assigned workspace state.

## Import

`from runa import AssignedWorkspace`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AssignedWorkspace(assigned: Literal[True], usage: EstimatedUsage)`

## Artifact docstring

Assigned workspace state.

Attributes:
    assigned: Literal ``True`` discriminator.
    usage: Estimated workspace usage.
Examples:
    See ``REF-EX-ASSIGNEDWORKSPACE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `assigned` | `Literal[True]` | Discriminator for the workspace union. |
| `usage` | `EstimatedUsage` | Estimated usage for an assigned workspace. |

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ASSIGNEDWORKSPACE` · `TC-091-09`

```python
def assigned_workspace(value: AssignedWorkspace) -> EstimatedUsage:
    return value.usage
```

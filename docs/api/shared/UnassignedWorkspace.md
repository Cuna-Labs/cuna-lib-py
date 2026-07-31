# `UnassignedWorkspace`

Unassigned workspace state.

## Import

`from runa import UnassignedWorkspace`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`UnassignedWorkspace(assigned: Literal[False], waitlist_position: int)`

## Artifact docstring

Unassigned workspace state.

Attributes:
    assigned: Literal ``False`` discriminator.
    waitlist_position: Current one-based waitlist position.
Examples:
    See ``REF-EX-UNASSIGNEDWORKSPACE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `assigned` | `Literal[False]` | Discriminator for the workspace union. |
| `waitlist_position` | `int` | Current one-based waitlist position. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-UNASSIGNEDWORKSPACE`; `TC-091-09`

```python
def unassigned_workspace(value: UnassignedWorkspace) -> int:
    return value.waitlist_position
```

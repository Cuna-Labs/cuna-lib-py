# `AssignedWorkspace`

Workspace state for an assigned account.

## Import

`from runa import AssignedWorkspace`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AssignedWorkspace(assigned: Literal[True], usage: EstimatedUsage)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`assigned`](#assigned) | `Literal[True]` | Discriminator for the workspace union. | `Literal[True]` | `ApiError` |

<a id="assigned"></a>
### `assigned`

Discriminator for the workspace union.

- Exact shape: `Literal[True]`
- Returns: `Literal[True]`
- Raises: `ApiError`

| [`usage`](#usage) | `EstimatedUsage` | Estimated usage for an assigned workspace. | `EstimatedUsage` | `ApiError` |

<a id="usage"></a>
### `usage`

Estimated usage for an assigned workspace.

- Exact shape: `EstimatedUsage`
- Returns: `EstimatedUsage`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ASSIGNEDWORKSPACE` · `TC-091-09`

```python
def assigned_workspace(value: AssignedWorkspace) -> EstimatedUsage:
    return value.usage
```

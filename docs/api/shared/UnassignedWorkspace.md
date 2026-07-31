# `UnassignedWorkspace`

Workspace state for a waitlisted account.

## Import

`from runa import UnassignedWorkspace`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`UnassignedWorkspace(assigned: Literal[False], waitlist_position: int)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`assigned`](#assigned) | `Literal[False]` | Discriminator for the workspace union. | `Literal[False]` | `ApiError` |

<a id="assigned"></a>
### `assigned`

Discriminator for the workspace union.

- Exact shape: `Literal[False]`
- Returns: `Literal[False]`
- Raises: `ApiError`

| [`waitlist_position`](#waitlist_position) | `int` | Current one-based waitlist position. | `int` | `ApiError` |

<a id="waitlist_position"></a>
### `waitlist_position`

Current one-based waitlist position.

- Exact shape: `int`
- Returns: `int`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-UNASSIGNEDWORKSPACE` · `TC-091-09`

```python
def unassigned_workspace(value: UnassignedWorkspace) -> int:
    return value.waitlist_position
```

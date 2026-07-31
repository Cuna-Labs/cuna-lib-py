# `Me`

Authenticated account and workspace state.

## Import

`from runa import Me`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Me(id: str, email: str, workspace: AssignedWorkspace | UnassignedWorkspace)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`id`](#id) | `str` | Canonical session UUID. | `str` | None |

<a id="id"></a>
### `id`

Canonical session UUID.

- Exact shape: `str`
- Returns: `str`
- Raises: None

| [`email`](#email) | `str` | Authenticated account email address. | `str` | `ApiError` |

<a id="email"></a>
### `email`

Authenticated account email address.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`workspace`](#workspace) | `AssignedWorkspace | UnassignedWorkspace` | Assigned or unassigned workspace state. | `AssignedWorkspace | UnassignedWorkspace` | `ApiError` |

<a id="workspace"></a>
### `workspace`

Assigned or unassigned workspace state.

- Exact shape: `AssignedWorkspace | UnassignedWorkspace`
- Returns: `AssignedWorkspace | UnassignedWorkspace`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ME` · `TC-091-09`

```python
def me(value: Me) -> str:
    return value.email
```

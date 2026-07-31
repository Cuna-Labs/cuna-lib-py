# `Me`

Authenticated account state.

## Import

`from runa import Me`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Me(id: str, email: str, workspace: AssignedWorkspace | UnassignedWorkspace)`

## Artifact docstring

Authenticated account state.

Attributes:
    id: Canonical account identifier.
    email: Authenticated email address.
    workspace: Assigned or unassigned workspace state.
Examples:
    See ``REF-EX-ME`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `id` | `str` | Canonical identifier. |
| `email` | `str` | Authenticated account email address. |
| `workspace` | `AssignedWorkspace | UnassignedWorkspace` | Assigned or unassigned workspace state. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ME`; `TC-091-09`

```python
def me(value: Me) -> str:
    return value.email
```

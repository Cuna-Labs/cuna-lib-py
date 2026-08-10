# `ProblemAction`

Closed recovery action supplied by a Runa API Problem response.

## Import

`from runa.errors import ProblemAction`

## Acquisition

Catch this type from `runa.errors`; root-module re-export is intentionally forbidden.

## Signature

``

## Artifact docstring

Closed recovery action supplied by a Runa API Problem response.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `RETRY` | `value` | Accepted `RETRY` value defined by the public contract. |
| `SIGN_IN` | `value` | Accepted `SIGN_IN` value defined by the public contract. |
| `OPEN_WEB` | `value` | Accepted `OPEN_WEB` value defined by the public contract. |
| `CONTACT_SUPPORT` | `value` | Accepted `CONTACT_SUPPORT` value defined by the public contract. |
| `NONE` | `value` | Accepted `NONE` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-PROBLEMACTION`; `TC-091-09`

```python
def problem_action() -> ProblemAction:
    return ProblemAction.NONE
```

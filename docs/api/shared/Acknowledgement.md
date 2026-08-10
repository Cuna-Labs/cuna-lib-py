# `Acknowledgement`

Immutable successful acknowledgement.

## Import

`from cuna import Acknowledgement`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Acknowledgement(ok: Literal[True])`

## Artifact docstring

Immutable successful acknowledgement.

Attributes:
    ok: Literal ``True``.
Examples:
    See ``REF-EX-ACKNOWLEDGEMENT`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `ok` | `Literal[True]` | Literal `True` acknowledgement. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ACKNOWLEDGEMENT`; `TC-091-09`

```python
def acknowledgement(value: Acknowledgement) -> bool:
    return value.ok
```

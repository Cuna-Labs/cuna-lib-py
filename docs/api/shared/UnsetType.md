# `UnsetType`

Type of the sole public omission marker, ``UNSET``.

## Import

`from cuna import UnsetType`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Type of the sole public omission marker, ``UNSET``.

Raises:
    TypeError: On every direct construction attempt.
Examples:
    See ``REF-EX-UNSETTYPE`` and ``TC-091-09``.

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-UNSETTYPE`; `TC-091-09`

```python
def unset_type(value: UnsetType) -> str:
    return repr(value)
```

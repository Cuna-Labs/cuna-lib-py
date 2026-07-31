# `UnsetType`

Nonconstructible type of the sole omission marker.

## Import

`from runa import UnsetType`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-UNSETTYPE` · `TC-091-09`

```python
def unset_type(value: UnsetType) -> str:
    return repr(value)
```

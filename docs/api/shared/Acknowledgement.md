# `Acknowledgement`

Immutable acknowledgement returned by accepted mutating operations.

## Import

`from runa import Acknowledgement`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Acknowledgement(ok: Literal[True])`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`ok`](#ok) | `Literal[True]` | Literal `True` acknowledgement. | `Literal[True]` | `ApiError` |

<a id="ok"></a>
### `ok`

Literal `True` acknowledgement.

- Exact shape: `Literal[True]`
- Returns: `Literal[True]`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ACKNOWLEDGEMENT` · `TC-091-09`

```python
def acknowledgement(value: Acknowledgement) -> bool:
    return value.ok
```

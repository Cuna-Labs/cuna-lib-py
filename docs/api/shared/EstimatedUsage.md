# `EstimatedUsage`

Estimated workspace spend and remaining balance.

## Import

`from runa import EstimatedUsage`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`EstimatedUsage(estimated_spend_usd: int | float, estimated_remaining_usd: int | float, note: str)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`estimated_spend_usd`](#estimated_spend_usd) | `int | float` | Estimated USD spend. | `int | float` | `ApiError` |

<a id="estimated_spend_usd"></a>
### `estimated_spend_usd`

Estimated USD spend.

- Exact shape: `int | float`
- Returns: `int | float`
- Raises: `ApiError`

| [`estimated_remaining_usd`](#estimated_remaining_usd) | `int | float` | Estimated remaining USD balance. | `int | float` | `ApiError` |

<a id="estimated_remaining_usd"></a>
### `estimated_remaining_usd`

Estimated remaining USD balance.

- Exact shape: `int | float`
- Returns: `int | float`
- Raises: `ApiError`

| [`note`](#note) | `str` | Service-provided usage note. | `str` | `ApiError` |

<a id="note"></a>
### `note`

Service-provided usage note.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ESTIMATEDUSAGE` · `TC-091-09`

```python
def estimated_usage(value: EstimatedUsage) -> float:
    return float(value.estimated_remaining_usd)
```

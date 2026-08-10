# `EstimatedUsage`

Estimated workspace usage.

## Import

`from cuna import EstimatedUsage`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`EstimatedUsage(estimated_spend_usd: int | float, estimated_remaining_usd: int | float, note: str)`

## Artifact docstring

Estimated workspace usage.

Attributes:
    estimated_spend_usd: Estimated USD spend.
    estimated_remaining_usd: Estimated remaining USD balance.
    note: Service-provided usage note.
Examples:
    See ``REF-EX-ESTIMATEDUSAGE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `estimated_spend_usd` | `int | float` | Estimated USD spend. |
| `estimated_remaining_usd` | `int | float` | Estimated remaining USD balance. |
| `note` | `str` | Service-provided usage note. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ESTIMATEDUSAGE`; `TC-091-09`

```python
def estimated_usage(value: EstimatedUsage) -> float:
    return float(value.estimated_remaining_usd)
```

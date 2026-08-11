# `CapabilityAvailability`

Current availability reported for a capability.

## Import

`from cuna import CapabilityAvailability`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Current availability reported for a capability.

Attributes:
    SUPPORTED: The capability is currently supported.
    UNSUPPORTED: The capability is not implemented.
    TEMPORARILY_UNAVAILABLE: The capability is known but not currently usable.
    UNKNOWN: Availability cannot be established safely.
Examples:
    See ``REF-EX-CAPABILITYAVAILABILITY`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `SUPPORTED` | `value` | Accepted `SUPPORTED` value defined by the public contract. |
| `UNSUPPORTED` | `value` | Accepted `UNSUPPORTED` value defined by the public contract. |
| `TEMPORARILY_UNAVAILABLE` | `value` | Accepted `TEMPORARILY_UNAVAILABLE` value defined by the public contract. |
| `UNKNOWN` | `value` | Accepted `UNKNOWN` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITYAVAILABILITY`; `TC-091-09`

```python
def capability_availability() -> CapabilityAvailability:
    return CapabilityAvailability.SUPPORTED
```

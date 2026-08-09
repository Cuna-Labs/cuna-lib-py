# `CapabilityMutationClass`

Consequence class of the operation behind a capability.

## Import

`from runa import CapabilityMutationClass`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Consequence class of the operation behind a capability.

Attributes:
    NONE: No mutation.
    REVERSIBLE: Reversible mutation.
    DESTRUCTIVE: Destructive mutation.
    SECRET_REVEALING: Operation may reveal a secret.
    FINANCIAL: Operation may create financial consequences.
Examples:
    See ``REF-EX-CAPABILITYMUTATIONCLASS`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `NONE` | `value` | Accepted `NONE` value defined by the public contract. |
| `REVERSIBLE` | `value` | Accepted `REVERSIBLE` value defined by the public contract. |
| `DESTRUCTIVE` | `value` | Accepted `DESTRUCTIVE` value defined by the public contract. |
| `SECRET_REVEALING` | `value` | Accepted `SECRET_REVEALING` value defined by the public contract. |
| `FINANCIAL` | `value` | Accepted `FINANCIAL` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITYMUTATIONCLASS`; `TC-091-09`

```python
def capability_mutation_class() -> CapabilityMutationClass:
    return CapabilityMutationClass.NONE
```

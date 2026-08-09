# `CapabilityInteraction`

Interaction required to use a capability.

## Import

`from runa import CapabilityInteraction`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Interaction required to use a capability.

Attributes:
    NATIVE: Native operation on the selected surface.
    READ_ONLY: Observation without mutation.
    BROWSER_HANDOFF: Browser-mediated handoff.
Examples:
    See ``REF-EX-CAPABILITYINTERACTION`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `NATIVE` | `value` | Accepted `NATIVE` value defined by the public contract. |
| `READ_ONLY` | `value` | Accepted `READ_ONLY` value defined by the public contract. |
| `BROWSER_HANDOFF` | `value` | Accepted `BROWSER_HANDOFF` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITYINTERACTION`; `TC-091-09`

```python
def capability_interaction() -> CapabilityInteraction:
    return CapabilityInteraction.READ_ONLY
```

# `Capability`

Immutable capability description returned by discovery.

## Import

`from runa import Capability`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Capability(id: str, availability: CapabilityAvailability, surfaces: tuple[CapabilitySurface, ...], interaction: CapabilityInteraction, mutation_class: CapabilityMutationClass, required_permissions: tuple[str, ...], reason_code: str | None = None)`

## Artifact docstring

Immutable capability description returned by discovery.

Attributes:
    id: Stable capability identifier.
    availability: Current availability.
    surfaces: Supported product surfaces.
    interaction: Required interaction mode.
    mutation_class: Consequence class.
    required_permissions: Permissions required by the protected operation.
    reason_code: Optional safe explanation for non-availability.
Examples:
    See ``REF-EX-CAPABILITY`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `id` | `str` | Canonical identifier. |
| `availability` | `CapabilityAvailability` | Current capability availability. |
| `surfaces` | `tuple[CapabilitySurface, ...]` | Product surfaces that expose the capability. |
| `interaction` | `CapabilityInteraction` | Required capability interaction mode. |
| `mutation_class` | `CapabilityMutationClass` | Capability consequence class. |
| `required_permissions` | `tuple[str, ...]` | Permissions required by the protected operation. |
| `reason_code` | `str | None` | Optional safe non-availability explanation. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITY`; `TC-091-09`

```python
def capability(value: Capability) -> CapabilityAvailability:
    return value.availability
```

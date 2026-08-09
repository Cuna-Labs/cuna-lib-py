# `CapabilitySurface`

Product surface on which a capability can be used.

## Import

`from runa import CapabilitySurface`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Product surface on which a capability can be used.

Attributes:
    CLI: Command-line interface.
    WEB: Authenticated web console.
    SDK: Public software development kit.
Examples:
    See ``REF-EX-CAPABILITYSURFACE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `CLI` | `value` | Accepted `CLI` value defined by the public contract. |
| `WEB` | `value` | Accepted `WEB` value defined by the public contract. |
| `SDK` | `value` | Accepted `SDK` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITYSURFACE`; `TC-091-09`

```python
def capability_surface() -> CapabilitySurface:
    return CapabilitySurface.SDK
```

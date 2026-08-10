# `TerminalConnectionAvailability`

Availability of one terminal stream capability.

## Import

`from cuna import TerminalConnectionAvailability`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Availability of one terminal stream capability.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `SUPPORTED` | `value` | Accepted `SUPPORTED` value defined by the public contract. |
| `UNSUPPORTED` | `value` | Accepted `UNSUPPORTED` value defined by the public contract. |
| `UNKNOWN` | `value` | Accepted `UNKNOWN` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-TERMINALCONNECTIONAVAILABILITY`; `TC-091-09`

```python
def terminal_connection_availability() -> TerminalConnectionAvailability:
    return TerminalConnectionAvailability.UNKNOWN
```

# `TerminalConnectionCapability`

One closed terminal stream capability record.

## Import

`from runa import TerminalConnectionCapability`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`TerminalConnectionCapability(name: TerminalConnectionCapabilityName, availability: TerminalConnectionAvailability)`

## Artifact docstring

One closed terminal stream capability record.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `name` | `TerminalConnectionCapabilityName` | Human-readable name. |
| `availability` | `TerminalConnectionAvailability` | Current capability availability. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-TERMINALCONNECTIONCAPABILITY`; `TC-091-09`

```python
def terminal_connection_capability(
    value: TerminalConnectionCapability,
) -> TerminalConnectionCapabilityName:
    return value.name
```

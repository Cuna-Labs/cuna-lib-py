# `TerminalConnectionCapabilityName`

Capability names negotiated for the terminal stream protocol.

## Import

`from runa import TerminalConnectionCapabilityName`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Capability names negotiated for the terminal stream protocol.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `ACKNOWLEDGEMENT` | `value` | Accepted `ACKNOWLEDGEMENT` value defined by the public contract. |
| `HEARTBEAT` | `value` | Accepted `HEARTBEAT` value defined by the public contract. |
| `LIVE_RESIZE` | `value` | Accepted `LIVE_RESIZE` value defined by the public contract. |
| `RESUME` | `value` | Accepted `RESUME` value defined by the public contract. |
| `SIGNALS` | `value` | Accepted `SIGNALS` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-TERMINALCONNECTIONCAPABILITYNAME`; `TC-091-09`

```python
def terminal_connection_capability_name() -> TerminalConnectionCapabilityName:
    return TerminalConnectionCapabilityName.ACKNOWLEDGEMENT
```

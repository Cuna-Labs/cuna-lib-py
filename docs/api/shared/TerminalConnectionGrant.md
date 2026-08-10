# `TerminalConnectionGrant`

Short-lived metadata grant; the SDK does not consume or open its stream.

## Import

`from cuna import TerminalConnectionGrant`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`TerminalConnectionGrant(terminal_session_id: str, resume_handle: str, connect_url: str, connect_token: str, protocol: Literal['cuna.terminal.v1', 'runa.terminal.v1'], capabilities: tuple[TerminalConnectionCapability, ...], expires_at: str)`

## Artifact docstring

Short-lived metadata grant; the SDK does not consume or open its stream.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `terminal_session_id` | `str` | Accepted `terminal_session_id` value defined by the public contract. |
| `resume_handle` | `str` | Accepted `resume_handle` value defined by the public contract. |
| `connect_url` | `str` | Accepted `connect_url` value defined by the public contract. |
| `connect_token` | `str` | Accepted `connect_token` value defined by the public contract. |
| `protocol` | `Literal['cuna.terminal.v1', 'runa.terminal.v1']` | Accepted `protocol` value defined by the public contract. |
| `capabilities` | `tuple[TerminalConnectionCapability, ...]` | Ordered capability descriptions. |
| `expires_at` | `str` | RFC 3339 evidence expiry timestamp. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-TERMINALCONNECTIONGRANT`; `TC-091-09`

```python
def terminal_connection_grant(value: TerminalConnectionGrant) -> str:
    return value.terminal_session_id
```

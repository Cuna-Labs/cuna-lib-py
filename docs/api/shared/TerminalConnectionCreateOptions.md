# `TerminalConnectionCreateOptions`

Caller-stable options for creating one terminal connection grant.

## Import

`from cuna import TerminalConnectionCreateOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`TerminalConnectionCreateOptions(idempotency_key: str, client_instance_id: str, resume_handle: str | None = None)`

## Artifact docstring

Caller-stable options for creating one terminal connection grant.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `idempotency_key` | `str` | Accepted `idempotency_key` value defined by the public contract. |
| `client_instance_id` | `str` | Accepted `client_instance_id` value defined by the public contract. |
| `resume_handle` | `str | None` | Accepted `resume_handle` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-TERMINALCONNECTIONCREATEOPTIONS`; `TC-091-09`

```python
def terminal_connection_create_options(value: TerminalConnectionCreateOptions) -> str:
    return value.client_instance_id
```

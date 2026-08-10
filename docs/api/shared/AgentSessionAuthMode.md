# `AgentSessionAuthMode`

Authentication binding selected for an AgentSession process.

## Import

`from cuna import AgentSessionAuthMode`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Authentication binding selected for an AgentSession process.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `INTERACTIVE_LOGIN` | `value` | Accepted `INTERACTIVE_LOGIN` value defined by the public contract. |
| `CREDENTIAL_BINDING` | `value` | Accepted `CREDENTIAL_BINDING` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONAUTHMODE`; `TC-091-09`

```python
def agent_session_auth_mode() -> AgentSessionAuthMode:
    return AgentSessionAuthMode.INTERACTIVE_LOGIN
```

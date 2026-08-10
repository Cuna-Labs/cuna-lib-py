# `AgentSessionAuthState`

Closed authentication evidence state for one AgentSession generation.

## Import

`from runa import AgentSessionAuthState`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Closed authentication evidence state for one AgentSession generation.

Attributes:
    LOGIN_REQUIRED: Interactive login has not completed.
    AUTHENTICATED: Provider CLI evidence confirms interactive authentication.
    CONFIGURED: Credential authority confirms the admitted binding is configured.
    UNAVAILABLE: The adapter cannot produce authoritative positive evidence.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `LOGIN_REQUIRED` | `value` | Accepted `LOGIN_REQUIRED` value defined by the public contract. |
| `AUTHENTICATED` | `value` | Accepted `AUTHENTICATED` value defined by the public contract. |
| `CONFIGURED` | `value` | Accepted `CONFIGURED` value defined by the public contract. |
| `UNAVAILABLE` | `value` | Accepted `UNAVAILABLE` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONAUTHSTATE`; `TC-091-09`

```python
def agent_session_auth_state() -> AgentSessionAuthState:
    return AgentSessionAuthState.AUTHENTICATED
```

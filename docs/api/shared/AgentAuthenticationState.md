# `AgentAuthenticationState`

Strict secret-free authentication state of a session agent.

## Import

`from runa import AgentAuthenticationState`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Strict secret-free authentication state of a session agent.

Attributes:
    NOT_APPLICABLE: The session has no agent authentication requirement.
    INSTALLING: The selected agent is still being installed.
    LOGIN_REQUIRED: Interactive login must be completed through the session terminal.
    AUTHENTICATED: The runtime probe confirms an interactive login.
    CONFIGURED: A usable API-key secret is configured for the agent.
    UNAVAILABLE: The agent runtime is not executable.
Examples:
    See ``REF-EX-AGENTAUTHENTICATIONSTATE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `NOT_APPLICABLE` | `value` | Accepted `NOT_APPLICABLE` value defined by the public contract. |
| `INSTALLING` | `value` | Accepted `INSTALLING` value defined by the public contract. |
| `LOGIN_REQUIRED` | `value` | Accepted `LOGIN_REQUIRED` value defined by the public contract. |
| `AUTHENTICATED` | `value` | Accepted `AUTHENTICATED` value defined by the public contract. |
| `CONFIGURED` | `value` | Accepted `CONFIGURED` value defined by the public contract. |
| `UNAVAILABLE` | `value` | Accepted `UNAVAILABLE` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTAUTHENTICATIONSTATE`; `TC-091-09`

```python
def agent_authentication_state() -> AgentAuthenticationState:
    return AgentAuthenticationState.AUTHENTICATED
```

# `AgentAuthenticationMethod`

Authentication method selected for a session agent.

## Import

`from runa import AgentAuthenticationMethod`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Authentication method selected for a session agent.

Attributes:
    NONE: No agent authentication applies.
    INTERACTIVE_LOGIN: Login is completed interactively in the session.
    API_KEY: Authentication is configured with a secret injected by the platform.
Examples:
    See ``REF-EX-AGENTAUTHENTICATIONMETHOD`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `NONE` | `value` | Accepted `NONE` value defined by the public contract. |
| `INTERACTIVE_LOGIN` | `value` | Accepted `INTERACTIVE_LOGIN` value defined by the public contract. |
| `API_KEY` | `value` | Accepted `API_KEY` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTAUTHENTICATIONMETHOD`; `TC-091-09`

```python
def agent_authentication_method() -> AgentAuthenticationMethod:
    return AgentAuthenticationMethod.INTERACTIVE_LOGIN
```

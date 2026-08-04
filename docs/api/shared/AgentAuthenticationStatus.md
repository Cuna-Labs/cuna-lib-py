# `AgentAuthenticationStatus`

Secret-free authentication status for a selected session agent.

## Import

`from runa import AgentAuthenticationStatus`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AgentAuthenticationStatus(agent: SessionAgent | None, method: AgentAuthenticationMethod, state: AgentAuthenticationState)`

## Artifact docstring

Secret-free authentication status for a selected session agent.

Attributes:
    agent: Selected agent, or ``None`` when the session has no agent.
    method: Authentication method configured for the agent.
    state: Current strict authentication state.
Examples:
    See ``REF-EX-AGENTAUTHENTICATIONSTATUS`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `agent` | `SessionAgent | None` | Selected agent; `UNSET` means omitted and `None` means absent in a response. |
| `method` | `AgentAuthenticationMethod` | Authentication method selected for the session agent. |
| `state` | `AgentAuthenticationState` | Strict secret-free authentication state of the session agent. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTAUTHENTICATIONSTATUS`; `TC-091-09`

```python
def agent_authentication_status(
    value: AgentAuthenticationStatus,
) -> AgentAuthenticationState:
    return value.state
```

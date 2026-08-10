# `AgentSessionRequestState`

Durable request processing state for an AgentSession.

## Import

`from cuna import AgentSessionRequestState`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Durable request processing state for an AgentSession.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `LAUNCH_PENDING` | `value` | Accepted `LAUNCH_PENDING` value defined by the public contract. |
| `RUNTIME_CLAIMED` | `value` | Accepted `RUNTIME_CLAIMED` value defined by the public contract. |
| `LAUNCHED` | `value` | Accepted `LAUNCHED` value defined by the public contract. |
| `TERMINATION_PENDING` | `value` | Accepted `TERMINATION_PENDING` value defined by the public contract. |
| `TERMINAL` | `value` | Accepted `TERMINAL` value defined by the public contract. |
| `FAILED` | `value` | Accepted `FAILED` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONREQUESTSTATE`; `TC-091-09`

```python
def agent_session_request_state() -> AgentSessionRequestState:
    return AgentSessionRequestState.LAUNCH_PENDING
```

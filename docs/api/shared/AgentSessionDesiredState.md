# `AgentSessionDesiredState`

Durable desired state for an AgentSession.

## Import

`from runa import AgentSessionDesiredState`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Durable desired state for an AgentSession.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `RUNNING` | `value` | Accepted `RUNNING` value defined by the public contract. |
| `TERMINATED` | `value` | Accepted `TERMINATED` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONDESIREDSTATE`; `TC-091-09`

```python
def agent_session_desired_state() -> AgentSessionDesiredState:
    return AgentSessionDesiredState.RUNNING
```

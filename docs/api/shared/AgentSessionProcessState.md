# `AgentSessionProcessState`

Observed process fact; ``UNKNOWN`` is not proof of absence.

## Import

`from cuna import AgentSessionProcessState`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Observed process fact; ``UNKNOWN`` is not proof of absence.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `UNKNOWN` | `value` | Accepted `UNKNOWN` value defined by the public contract. |
| `STARTING` | `value` | Accepted `STARTING` value defined by the public contract. |
| `READY` | `value` | Accepted `READY` value defined by the public contract. |
| `RUNNING` | `value` | Accepted `RUNNING` value defined by the public contract. |
| `EXITED` | `value` | Accepted `EXITED` value defined by the public contract. |
| `FAILED` | `value` | Accepted `FAILED` value defined by the public contract. |
| `TERMINATING` | `value` | Accepted `TERMINATING` value defined by the public contract. |
| `TERMINATED` | `value` | Accepted `TERMINATED` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONPROCESSSTATE`; `TC-091-09`

```python
def agent_session_process_state() -> AgentSessionProcessState:
    return AgentSessionProcessState.UNKNOWN
```

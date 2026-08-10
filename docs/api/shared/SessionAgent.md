# `SessionAgent`

Supported session agent.

## Import

`from cuna import SessionAgent`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Supported session agent.

Attributes:
    CLAUDE_CODE: Claude Code agent.
    CODEX: Codex agent.
    OPENCLAW: OpenClaw agent.
Examples:
    See ``REF-EX-SESSIONAGENT`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `CLAUDE_CODE` | `value` | Accepted `CLAUDE_CODE` value defined by the public contract. |
| `CODEX` | `value` | Accepted `CODEX` value defined by the public contract. |
| `OPENCLAW` | `value` | Accepted `OPENCLAW` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-SESSIONAGENT`; `TC-091-09`

```python
def session_agent() -> SessionAgent:
    return SessionAgent.CODEX
```

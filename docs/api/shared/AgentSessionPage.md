# `AgentSessionPage`

One bounded AgentSession page with an opaque continuation cursor.

## Import

`from cuna import AgentSessionPage`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AgentSessionPage(items: tuple[AgentSession, ...], next_cursor: str | None = None)`

## Artifact docstring

One bounded AgentSession page with an opaque continuation cursor.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `items` | `tuple[AgentSession, ...]` | Accepted `items` value defined by the public contract. |
| `next_cursor` | `str | None` | Accepted `next_cursor` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONPAGE`; `TC-091-09`

```python
def agent_session_page(value: AgentSessionPage) -> tuple[AgentSession, ...]:
    return value.items
```

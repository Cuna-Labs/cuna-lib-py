# `AgentSessionListOptions`

Optional bounded pagination controls for AgentSession listing.

## Import

`from runa import AgentSessionListOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AgentSessionListOptions(limit: int | None = None, cursor: str | None = None)`

## Artifact docstring

Optional bounded pagination controls for AgentSession listing.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `limit` | `int | None` | Accepted `limit` value defined by the public contract. |
| `cursor` | `str | None` | Accepted `cursor` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONLISTOPTIONS`; `TC-091-09`

```python
def agent_session_list_options(value: AgentSessionListOptions) -> int | None:
    return value.limit
```

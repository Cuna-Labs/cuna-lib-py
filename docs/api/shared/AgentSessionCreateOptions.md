# `AgentSessionCreateOptions`

AgentSession creation request and caller-stable idempotency identity.

## Import

`from runa import AgentSessionCreateOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AgentSessionCreateOptions(idempotency_key: str, agent: SessionAgent, cwd: str, workspace_binding_id: str, workspace_generation: int, name: str | None = None, auth_mode: AgentSessionAuthMode | None = None, credential_binding_id: str | None = None)`

## Artifact docstring

AgentSession creation request and caller-stable idempotency identity.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `idempotency_key` | `str` | Accepted `idempotency_key` value defined by the public contract. |
| `agent` | `SessionAgent` | Selected agent; `UNSET` means omitted and `None` means absent in a response. |
| `cwd` | `str` | Command working directory; `UNSET` means omitted. |
| `workspace_binding_id` | `str` | Accepted `workspace_binding_id` value defined by the public contract. |
| `workspace_generation` | `int` | Accepted `workspace_generation` value defined by the public contract. |
| `name` | `str | None` | Human-readable name. |
| `auth_mode` | `AgentSessionAuthMode | None` | Accepted `auth_mode` value defined by the public contract. |
| `credential_binding_id` | `str | None` | Accepted `credential_binding_id` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONCREATEOPTIONS`; `TC-091-09`

```python
def agent_session_create_options(value: AgentSessionCreateOptions) -> str:
    return value.workspace_binding_id
```

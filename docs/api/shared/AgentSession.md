# `AgentSession`

Immutable AgentSession intent and observed process facts.

## Import

`from cuna import AgentSession`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AgentSession(id: str, machine_id: str, name: str, agent: SessionAgent, cwd: str, auth_mode: AgentSessionAuthMode, desired_state: AgentSessionDesiredState, request_state: AgentSessionRequestState, process_state: AgentSessionProcessState, row_version: int, created_at: str, updated_at: str, workspace_binding_id: str | None = None, workspace_generation: int | None = None, process_epoch: str | None = None, runtime_observed_at: str | None = None, runtime_expires_at: str | None = None, termination_requested_at: str | None = None)`

## Artifact docstring

Immutable AgentSession intent and observed process facts.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `id` | `str` | Canonical identifier. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `name` | `str` | Human-readable name. |
| `agent` | `SessionAgent` | Selected agent; `UNSET` means omitted and `None` means absent in a response. |
| `cwd` | `str` | Command working directory; `UNSET` means omitted. |
| `auth_mode` | `AgentSessionAuthMode` | Accepted `auth_mode` value defined by the public contract. |
| `desired_state` | `AgentSessionDesiredState` | Accepted `desired_state` value defined by the public contract. |
| `request_state` | `AgentSessionRequestState` | Accepted `request_state` value defined by the public contract. |
| `process_state` | `AgentSessionProcessState` | Accepted `process_state` value defined by the public contract. |
| `row_version` | `int` | Accepted `row_version` value defined by the public contract. |
| `created_at` | `str` | Service timestamp encoded as an RFC 3339 string. |
| `updated_at` | `str` | Service timestamp encoded as an RFC 3339 string. |
| `workspace_binding_id` | `str | None` | Accepted `workspace_binding_id` value defined by the public contract. |
| `workspace_generation` | `int | None` | Accepted `workspace_generation` value defined by the public contract. |
| `process_epoch` | `str | None` | Accepted `process_epoch` value defined by the public contract. |
| `runtime_observed_at` | `str | None` | Accepted `runtime_observed_at` value defined by the public contract. |
| `runtime_expires_at` | `str | None` | Accepted `runtime_expires_at` value defined by the public contract. |
| `termination_requested_at` | `str | None` | Accepted `termination_requested_at` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSION`; `TC-091-09`

```python
def agent_session(value: AgentSession) -> str:
    return value.workspace_binding_id or value.id
```

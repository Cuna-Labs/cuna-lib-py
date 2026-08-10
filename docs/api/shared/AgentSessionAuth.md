# `AgentSessionAuth`

Immutable short-lived evidence for one exact AgentSession process generation.

## Import

`from cuna import AgentSessionAuth`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AgentSessionAuth(observation_id: str, agent_session_id: str, process_epoch: str | None, auth_mode: AgentSessionAuthMode, agent_version: str, adapter_version: Literal['cuna.agent-auth.v1', 'runa.agent-auth.v1'], evidence_class: AgentSessionAuthEvidenceClass, observed_at: str, valid_until: str, state: AgentSessionAuthState)`

## Artifact docstring

Immutable short-lived evidence for one exact AgentSession process generation.

Attributes:
    observation_id: Canonical UUID of this observation.
    agent_session_id: Exact AgentSession UUID to which the evidence belongs.
    process_epoch: Exact process generation UUID, or no epoch for negative evidence.
    auth_mode: Authentication mode admitted for the AgentSession.
    agent_version: Observed provider-agent semantic version.
    adapter_version: Closed Cuna authentication-adapter contract version,
        exactly as the service minted it. Both brand spellings are accepted
        and the value is echoed, never normalized.
    evidence_class: Authority class that produced the observation.
    observed_at: RFC 3339 observation timestamp.
    valid_until: RFC 3339 expiry no more than 30 seconds after observation.
    state: Closed secret-free authentication evidence state.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `observation_id` | `str` | Accepted `observation_id` value defined by the public contract. |
| `agent_session_id` | `str` | Accepted `agent_session_id` value defined by the public contract. |
| `process_epoch` | `str | None` | Accepted `process_epoch` value defined by the public contract. |
| `auth_mode` | `AgentSessionAuthMode` | Accepted `auth_mode` value defined by the public contract. |
| `agent_version` | `str` | Accepted `agent_version` value defined by the public contract. |
| `adapter_version` | `Literal['cuna.agent-auth.v1', 'runa.agent-auth.v1']` | Accepted `adapter_version` value defined by the public contract. |
| `evidence_class` | `AgentSessionAuthEvidenceClass` | Accepted `evidence_class` value defined by the public contract. |
| `observed_at` | `str` | RFC 3339 observation timestamp. |
| `valid_until` | `str` | Accepted `valid_until` value defined by the public contract. |
| `state` | `AgentSessionAuthState` | Strict secret-free authentication state of the session agent. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONAUTH`; `TC-091-09`

```python
def agent_session_auth(value: AgentSessionAuth) -> AgentSessionAuthState:
    return value.state
```

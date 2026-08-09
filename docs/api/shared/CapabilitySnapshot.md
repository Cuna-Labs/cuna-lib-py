# `CapabilitySnapshot`

Leased capability evidence for one account, machine, or AgentSession.

## Import

`from runa import CapabilitySnapshot`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`CapabilitySnapshot(schema_version: Literal['1.0'], subject_scope: Literal[CapabilityScope.ACCOUNT, CapabilityScope.MACHINE, CapabilityScope.AGENT_SESSION], subject_id: str | None, observed_at: str, expires_at: str, etag: str, capabilities: tuple[Capability, ...])`

## Artifact docstring

Leased capability evidence for one account, machine, or AgentSession.

Attributes:
    schema_version: Capability schema version.
    subject_scope: Account, machine, or AgentSession scope represented by the snapshot.
    subject_id: Machine or AgentSession UUID for resource-scoped evidence.
    observed_at: RFC 3339 observation timestamp.
    expires_at: RFC 3339 evidence expiry timestamp.
    etag: Unquoted semantic evidence digest.
    capabilities: Ordered capability descriptions.
Examples:
    See ``REF-EX-CAPABILITYSNAPSHOT`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `schema_version` | `Literal['1.0']` | Capability schema version. |
| `subject_scope` | `Literal[CapabilityScope.ACCOUNT, CapabilityScope.MACHINE, CapabilityScope.AGENT_SESSION]` | Account, machine, or AgentSession scope represented by the snapshot. |
| `subject_id` | `str | None` | Machine or AgentSession UUID for resource-scoped evidence. |
| `observed_at` | `str` | RFC 3339 observation timestamp. |
| `expires_at` | `str` | RFC 3339 evidence expiry timestamp. |
| `etag` | `str` | Unquoted semantic evidence digest. |
| `capabilities` | `tuple[Capability, ...]` | Ordered capability descriptions. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITYSNAPSHOT`; `TC-091-09`

```python
def capability_snapshot(value: CapabilitySnapshot) -> tuple[Capability, ...]:
    return value.capabilities
```

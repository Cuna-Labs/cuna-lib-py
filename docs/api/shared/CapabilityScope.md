# `CapabilityScope`

Scope accepted by capability discovery.

## Import

`from runa import CapabilityScope`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Scope accepted by capability discovery.

Attributes:
    ACCOUNT: Account-wide capability evidence.
    MACHINE: Evidence for one machine UUID.
    AGENT_SESSION: Evidence for one AgentSession UUID.
Examples:
    See ``REF-EX-CAPABILITYSCOPE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `ACCOUNT` | `value` | Accepted `ACCOUNT` value defined by the public contract. |
| `MACHINE` | `value` | Accepted `MACHINE` value defined by the public contract. |
| `AGENT_SESSION` | `value` | Accepted `AGENT_SESSION` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITYSCOPE`; `TC-091-09`

```python
def capability_scope() -> CapabilityScope:
    return CapabilityScope.ACCOUNT
```

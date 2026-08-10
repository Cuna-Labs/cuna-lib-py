# `AgentSessionAuthEvidenceClass`

Authority class that produced an AgentSession authentication observation.

## Import

`from runa import AgentSessionAuthEvidenceClass`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Authority class that produced an AgentSession authentication observation.

Attributes:
    PROVIDER_CLI_LOGIN_STATUS: Evidence read from the provider CLI authority.
    CREDENTIAL_BINDING_AUTHORITY: Evidence read from Cuna's binding authority.
    INSUFFICIENT: Negative evidence because no positive authority was available.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `PROVIDER_CLI_LOGIN_STATUS` | `value` | Accepted `PROVIDER_CLI_LOGIN_STATUS` value defined by the public contract. |
| `CREDENTIAL_BINDING_AUTHORITY` | `value` | Accepted `CREDENTIAL_BINDING_AUTHORITY` value defined by the public contract. |
| `INSUFFICIENT` | `value` | Accepted `INSUFFICIENT` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-AGENTSESSIONAUTHEVIDENCECLASS`; `TC-091-09`

```python
def agent_session_auth_evidence_class() -> AgentSessionAuthEvidenceClass:
    return AgentSessionAuthEvidenceClass.PROVIDER_CLI_LOGIN_STATUS
```

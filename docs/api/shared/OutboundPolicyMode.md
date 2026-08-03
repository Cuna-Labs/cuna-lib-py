# `OutboundPolicyMode`

Public outbound network policy mode.

## Import

`from runa import OutboundPolicyMode`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Artifact docstring

Public outbound network policy mode.

Attributes:
    ALLOWLIST: Permit only listed work destinations.
    DENYLIST: Block listed work destinations and permit the others.
Examples:
    See ``REF-EX-OUTBOUNDPOLICYMODE`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `ALLOWLIST` | `value` | Accepted `ALLOWLIST` value defined by the public contract. |
| `DENYLIST` | `value` | Accepted `DENYLIST` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-OUTBOUNDPOLICYMODE`; `TC-091-09`

```python
def outbound_policy_mode() -> OutboundPolicyMode:
    return OutboundPolicyMode.ALLOWLIST
```

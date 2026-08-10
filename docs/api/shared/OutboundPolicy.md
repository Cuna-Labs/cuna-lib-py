# `OutboundPolicy`

Allow-list or deny-list policy for a newly created session.

## Import

`from cuna import OutboundPolicy`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`OutboundPolicy(mode: OutboundPolicyMode, hosts: list[str])`

## Artifact docstring

Allow-list or deny-list policy for a newly created session.

An empty ``hosts`` list is explicit and retains the selected mode's semantics.

Attributes:
    mode: Selected allow-list or deny-list behavior.
    hosts: Exact-domain or leading-wildcard host rules.
Examples:
    See ``REF-EX-OUTBOUNDPOLICY`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `mode` | `OutboundPolicyMode` | Accepted `mode` value defined by the public contract. |
| `hosts` | `list[str]` | Accepted `hosts` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-OUTBOUNDPOLICY`; `TC-091-09`

```python
def outbound_policy() -> OutboundPolicy:
    return OutboundPolicy(OutboundPolicyMode.DENYLIST, ["tracking.example.com"])
```

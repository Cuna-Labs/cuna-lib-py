# `Record`

Immutable workspace record.

## Import

`from runa import Record`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Record(id: str, session_id: str, kind: str, summary: str, detail: object, created_at: str)`

## Artifact docstring

Immutable workspace record.

Attributes:
    id: Canonical record identifier.
    session_id: Canonical parent session UUID.
    kind: Record kind discriminator.
    summary: Disclosure-safe summary.
    detail: Contract-defined detail retained without hidden filtering.
    created_at: RFC 3339 creation timestamp.
Examples:
    See ``REF-EX-RECORD`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `id` | `str` | Canonical identifier. |
| `session_id` | `str` | Canonical parent session UUID. |
| `kind` | `str` | Record kind discriminator. |
| `summary` | `str` | Disclosure-safe record summary. |
| `detail` | `object` | Contract-defined record detail retained without hidden filtering. |
| `created_at` | `str` | Service timestamp encoded as an RFC 3339 string. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-RECORD`; `TC-091-09`

```python
def record(value: Record) -> str:
    return value.summary
```

# `Record`

Immutable record visible to the authenticated workspace.

## Import

`from runa import Record`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`Record(id: str, session_id: str, kind: str, summary: str, detail: object, created_at: str)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`id`](#id) | `str` | Canonical session UUID. | `str` | None |

<a id="id"></a>
### `id`

Canonical session UUID.

- Exact shape: `str`
- Returns: `str`
- Raises: None

| [`session_id`](#session_id) | `str` | Canonical parent session UUID. | `str` | `ApiError` |

<a id="session_id"></a>
### `session_id`

Canonical parent session UUID.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`kind`](#kind) | `str` | Record kind discriminator. | `str` | `ApiError` |

<a id="kind"></a>
### `kind`

Record kind discriminator.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`summary`](#summary) | `str` | Disclosure-safe record summary. | `str` | `ApiError` |

<a id="summary"></a>
### `summary`

Disclosure-safe record summary.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`detail`](#detail) | `object` | Contract-defined record detail retained without hidden filtering. | `object` | `ApiError` |

<a id="detail"></a>
### `detail`

Contract-defined record detail retained without hidden filtering.

- Exact shape: `object`
- Returns: `object`
- Raises: `ApiError`

| [`created_at`](#created_at) | `str` | Service timestamp encoded as an RFC 3339 string. | `str` | `ApiError` |

<a id="created_at"></a>
### `created_at`

Service timestamp encoded as an RFC 3339 string.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-RECORD` · `TC-091-09`

```python
def record(value: Record) -> str:
    return value.summary
```

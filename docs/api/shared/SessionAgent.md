# `SessionAgent`

Closed set of supported session agents.

## Import

`from runa import SessionAgent`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

``

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`CLAUDE_CODE`](#CLAUDE_CODE) | `value` | Accepted `CLAUDE_CODE` value defined by the public contract. | `value` | `ApiError` |

<a id="CLAUDE_CODE"></a>
### `CLAUDE_CODE`

Accepted `CLAUDE_CODE` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`CODEX`](#CODEX) | `value` | Accepted `CODEX` value defined by the public contract. | `value` | `ApiError` |

<a id="CODEX"></a>
### `CODEX`

Accepted `CODEX` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

| [`OPENCLAW`](#OPENCLAW) | `value` | Accepted `OPENCLAW` value defined by the public contract. | `value` | `ApiError` |

<a id="OPENCLAW"></a>
### `OPENCLAW`

Accepted `OPENCLAW` value defined by the public contract.

- Exact shape: `value`
- Returns: `value`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-SESSIONAGENT` · `TC-091-09`

```python
def session_agent() -> SessionAgent:
    return SessionAgent.CODEX
```

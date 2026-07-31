# `RunaError`

Immutable nonconstructible base of normalized SDK errors.

## Import

`from runa.errors import RunaError`

## Acquisition

Catch this type from `runa.errors`; root-module re-export is intentionally forbidden.

## Signature

`RunaError(code: ErrorCode)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`code`](#code) | `ErrorCode` | Stable disclosure-safe error category. | `ErrorCode` | None |

<a id="code"></a>
### `code`

Stable disclosure-safe error category.

- Exact shape: `ErrorCode`
- Returns: `ErrorCode`
- Raises: None

| [`message`](#message) | `str` | Stable disclosure-safe English error message. | `str` | None |

<a id="message"></a>
### `message`

Stable disclosure-safe English error message.

- Exact shape: `str`
- Returns: `str`
- Raises: None

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-RUNAERROR` · `TC-091-09`

```python
def runa_error(error: RunaError) -> str:
    return error.code
```

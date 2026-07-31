# `RunaError`

Nonconstructible common base for normalized SDK errors.

## Import

`from runa.errors import RunaError`

## Acquisition

Catch this type from `runa.errors`; root-module re-export is intentionally forbidden.

## Signature

`RunaError(code: ErrorCode)`

## Artifact docstring

Nonconstructible common base for normalized SDK errors.

Attributes:
    code: Stable disclosure-safe error category.
    message: Stable disclosure-safe English message.
Raises:
    TypeError: On direct construction.
Examples:
    See ``REF-EX-RUNAERROR`` and ``TC-091-09``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`code`](#code) | `ErrorCode` | Return the stable error category. | `ErrorCode` | None |

<a id="code"></a>
### `code`

Return the stable error category.

- Exact shape: `ErrorCode`
- Returns: `ErrorCode`
- Raises: None

Return the stable error category.

Returns:
    One accepted ``ErrorCode`` literal.
Examples:
    See ``REF-EX-RUNAERROR`` and ``TC-091-09``.

| [`message`](#message) | `str` | Return the stable disclosure-safe message. | `str` | None |

<a id="message"></a>
### `message`

Return the stable disclosure-safe message.

- Exact shape: `str`
- Returns: `str`
- Raises: None

Return the stable disclosure-safe message.

Returns:
    The normalized English error message.
Examples:
    See ``REF-EX-RUNAERROR`` and ``TC-091-09``.

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-RUNAERROR` · `TC-091-09`

```python
def runa_error(error: RunaError) -> str:
    return error.code
```

# `ApiError`

Safe API, transport, status, or malformed-response failure.

## Import

`from runa.errors import ApiError`

## Acquisition

Catch this type from `runa.errors`; root-module re-export is intentionally forbidden.

## Signature

`ApiError(status: int, *, code: Literal['api_error', 'malformed_response'] = 'api_error')`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`status`](#status) | `int` | HTTP status associated with this API failure. | `int` | None |

<a id="status"></a>
### `status`

HTTP status associated with this API failure.

- Exact shape: `int`
- Returns: `int`
- Raises: None

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-APIERROR` · `TC-091-09`

```python
def api_error(error: ApiError) -> int:
    return error.status
```

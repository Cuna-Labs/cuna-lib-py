# `OpenSessionResult`

Capability-bearing result returned when opening a session.

## Import

`from runa import OpenSessionResult`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`OpenSessionResult(url: str)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`url`](#url) | `str` | Sensitive capability URL; never log, display, persist, or reuse. | `str` | `ApiError` |

<a id="url"></a>
### `url`

Sensitive capability URL; never log, display, persist, or reuse.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-OPENSESSIONRESULT` · `TC-091-09`

```python
def open_session_result(value: OpenSessionResult) -> None:
    result = value
    del result
```

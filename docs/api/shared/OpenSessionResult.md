# `OpenSessionResult`

Sensitive open-session result.

## Import

`from cuna import OpenSessionResult`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`OpenSessionResult(url: str)`

## Artifact docstring

Sensitive open-session result.

Attributes:
    url: Capability URL; assign it and never log, display, persist, or reuse it.
Examples:
    See ``REF-EX-OPENSESSIONRESULT`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `url` | `str` | Sensitive capability URL; never log, display, persist, or reuse. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-OPENSESSIONRESULT`; `TC-091-09`

```python
def open_session_result(value: OpenSessionResult) -> None:
    result = value
    del result
```

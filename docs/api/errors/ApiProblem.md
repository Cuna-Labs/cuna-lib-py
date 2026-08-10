# `ApiProblem`

Validated RFC 9457-style Cuna API problem details.

## Import

`from cuna.errors import ApiProblem`

## Acquisition

Catch this type from `cuna.errors`; root-module re-export is intentionally forbidden.

## Signature

`ApiProblem(type: str, title: str, status: int, code: str, request_id: str, retryable: bool, detail: str | None = None, action: ProblemAction | None = None)`

## Artifact docstring

Validated RFC 9457-style Cuna API problem details.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `type` | `str` | Accepted `type` value defined by the public contract. |
| `title` | `str` | Accepted `title` value defined by the public contract. |
| `status` | `int` | Current lifecycle state. |
| `code` | `str` | Accepted `code` value defined by the public contract. |
| `request_id` | `str` | Accepted `request_id` value defined by the public contract. |
| `retryable` | `bool` | Accepted `retryable` value defined by the public contract. |
| `detail` | `str | None` | Contract-defined record detail retained without hidden filtering. |
| `action` | `ProblemAction | None` | Accepted `action` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-APIPROBLEM`; `TC-091-09`

```python
def api_problem(error: ApiProblem) -> str:
    return error.code
```

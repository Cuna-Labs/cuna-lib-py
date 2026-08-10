# `ApiError`

Safe API or malformed-response failure.

## Import

`from cuna.errors import ApiError`

## Acquisition

Catch this type from `cuna.errors`; root-module re-export is intentionally forbidden.

## Signature

`ApiError(status: int, *, code: Literal['api_error', 'malformed_response'] = 'api_error', problem: ApiProblem | WorkspaceSyncProblem | None = None)`

## Artifact docstring

Safe API or malformed-response failure.

Args:
    status: HTTP status associated with the failure.
    code: ``api_error`` or ``malformed_response``.
    problem: Validated Problem body associated with this failure, when supplied.
Raises:
    TypeError: If ``status`` is not exactly an integer.
Examples:
    See ``REF-EX-APIERROR`` and ``TC-091-09``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`status`](#status) | `int` | Return the associated HTTP status. | `int` | None |

<a id="status"></a>
### `status`

Return the associated HTTP status.

- Exact shape: `int`
- Returns: `int`
- Raises: None

Return the associated HTTP status.

Returns:
    The exact integer supplied by the SDK failure path.
Examples:
    See ``REF-EX-APIERROR`` and ``TC-091-09``.

| [`problem`](#problem) | `ApiProblem | WorkspaceSyncProblem | None` | Return a validated Problem body, when the service supplied one. | `ApiProblem | WorkspaceSyncProblem | None` | None |

<a id="problem"></a>
### `problem`

Return a validated Problem body, when the service supplied one.

- Exact shape: `ApiProblem | WorkspaceSyncProblem | None`
- Returns: `ApiProblem | WorkspaceSyncProblem | None`
- Raises: None

Return a validated Problem body, when the service supplied one.

Returns:
    The validated Problem body, or ``None`` when no body was supplied.
Examples:
    See ``REF-EX-APIERROR`` and ``TC-091-09``.

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-APIERROR`; `TC-091-09`

```python
def api_error(error: ApiError) -> int:
    return error.status
```

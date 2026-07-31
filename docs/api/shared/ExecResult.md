# `ExecResult`

Immutable result of a completed session command.

## Import

`from runa import ExecResult`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`ExecResult(exit_code: int, stdout: str, stderr: str, duration_ms: int, stdout_truncated: bool, stderr_truncated: bool)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`exit_code`](#exit_code) | `int` | Process exit code. | `int` | `ApiError` |

<a id="exit_code"></a>
### `exit_code`

Process exit code.

- Exact shape: `int`
- Returns: `int`
- Raises: `ApiError`

| [`stdout`](#stdout) | `str` | Captured standard output. | `str` | `ApiError` |

<a id="stdout"></a>
### `stdout`

Captured standard output.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`stderr`](#stderr) | `str` | Captured standard error. | `str` | `ApiError` |

<a id="stderr"></a>
### `stderr`

Captured standard error.

- Exact shape: `str`
- Returns: `str`
- Raises: `ApiError`

| [`duration_ms`](#duration_ms) | `int` | Command duration in milliseconds. | `int` | `ApiError` |

<a id="duration_ms"></a>
### `duration_ms`

Command duration in milliseconds.

- Exact shape: `int`
- Returns: `int`
- Raises: `ApiError`

| [`stdout_truncated`](#stdout_truncated) | `bool` | Whether standard output was truncated. | `bool` | `ApiError` |

<a id="stdout_truncated"></a>
### `stdout_truncated`

Whether standard output was truncated.

- Exact shape: `bool`
- Returns: `bool`
- Raises: `ApiError`

| [`stderr_truncated`](#stderr_truncated) | `bool` | Whether standard error was truncated. | `bool` | `ApiError` |

<a id="stderr_truncated"></a>
### `stderr_truncated`

Whether standard error was truncated.

- Exact shape: `bool`
- Returns: `bool`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-EXECRESULT` · `TC-091-09`

```python
def exec_result(value: ExecResult) -> int:
    return value.exit_code
```

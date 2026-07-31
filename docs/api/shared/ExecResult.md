# `ExecResult`

Immutable command result.

## Import

`from runa import ExecResult`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`ExecResult(exit_code: int, stdout: str, stderr: str, duration_ms: int, stdout_truncated: bool, stderr_truncated: bool)`

## Artifact docstring

Immutable command result.

Attributes:
    exit_code: Process exit code.
    stdout: Captured standard output.
    stderr: Captured standard error.
    duration_ms: Command duration in milliseconds.
    stdout_truncated: Whether standard output was truncated.
    stderr_truncated: Whether standard error was truncated.
Examples:
    See ``REF-EX-EXECRESULT`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `exit_code` | `int` | Process exit code. |
| `stdout` | `str` | Captured standard output. |
| `stderr` | `str` | Captured standard error. |
| `duration_ms` | `int` | Command duration in milliseconds. |
| `stdout_truncated` | `bool` | Whether standard output was truncated. |
| `stderr_truncated` | `bool` | Whether standard error was truncated. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-EXECRESULT`; `TC-091-09`

```python
def exec_result(value: ExecResult) -> int:
    return value.exit_code
```

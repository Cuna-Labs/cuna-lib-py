# `ExecOptions`

Omission-aware command execution options.

## Import

`from runa import ExecOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`ExecOptions(cwd: str | UnsetType = UNSET, timeout_secs: int | UnsetType = UNSET)`

## Artifact docstring

Omission-aware command execution options.

Attributes:
    cwd: Working directory or ``UNSET``.
    timeout_secs: Integer from 1 through 600 or ``UNSET``.
Examples:
    See ``REF-EX-EXECOPTIONS`` and ``TC-091-09``.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `cwd` | `str | UnsetType` | Command working directory; `UNSET` means omitted. |
| `timeout_secs` | `int | UnsetType` | Execution timeout 1-600 seconds; `UNSET` means omitted. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-EXECOPTIONS`; `TC-091-09`

```python
def exec_options() -> ExecOptions:
    return ExecOptions(cwd="/workspace", timeout_secs=30)
```

# `ExecOptions`

Optional, omission-aware inputs for command execution.

## Import

`from runa import ExecOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`ExecOptions(cwd: str | UnsetType = UNSET, timeout_secs: int | UnsetType = UNSET)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`cwd`](#cwd) | `str | UnsetType` | Command working directory; `UNSET` means omitted. | `str | UnsetType` | `ApiError` |

<a id="cwd"></a>
### `cwd`

Command working directory; `UNSET` means omitted.

- Exact shape: `str | UnsetType`
- Returns: `str | UnsetType`
- Raises: `ApiError`

| [`timeout_secs`](#timeout_secs) | `int | UnsetType` | Execution timeout 1-600 seconds; `UNSET` means omitted. | `int | UnsetType` | `ApiError` |

<a id="timeout_secs"></a>
### `timeout_secs`

Execution timeout 1-600 seconds; `UNSET` means omitted.

- Exact shape: `int | UnsetType`
- Returns: `int | UnsetType`
- Raises: `ApiError`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-EXECOPTIONS` · `TC-091-09`

```python
def exec_options() -> ExecOptions:
    return ExecOptions(cwd="/workspace", timeout_secs=30)
```

# `CommandError`

Reserved nonconstructible compatibility error; v1 never raises it.

## Import

`from runa.errors import CommandError`

## Acquisition

Catch this type from `runa.errors`; root-module re-export is intentionally forbidden.

## Signature

`CommandError()`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-COMMANDERROR` · `TC-091-09`

```python
def command_error(error: CommandError) -> str:
    return error.code
```

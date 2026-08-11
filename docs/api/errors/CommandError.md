# `CommandError`

Reserved compatibility type; no SDK v1 path constructs or raises it.

## Import

`from cuna.errors import CommandError`

## Acquisition

Catch this type from `cuna.errors`; root-module re-export is intentionally forbidden.

## Signature

`CommandError()`

## Artifact docstring

Reserved compatibility type; no SDK v1 path constructs or raises it.

Raises:
    TypeError: On every construction attempt.
Examples:
    See ``REF-EX-COMMANDERROR`` and ``TC-091-09``.

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-COMMANDERROR`; `TC-091-09`

```python
def command_error(error: CommandError) -> str:
    return error.code
```

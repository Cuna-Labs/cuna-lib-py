# `ConfigError`

Safe configuration or local-input failure.

## Import

`from runa.errors import ConfigError`

## Acquisition

Catch this type from `runa.errors`; root-module re-export is intentionally forbidden.

## Signature

`ConfigError()`

## Artifact docstring

Safe configuration or local-input failure.

Examples:
    See ``REF-EX-CONFIGERROR`` and ``TC-091-09``.

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CONFIGERROR`; `TC-091-09`

```python
def config_error(error: ConfigError) -> str:
    return error.message
```

# `ConfigError`

Safe configuration or local-input failure.

## Import

`from runa.errors import ConfigError`

## Acquisition

Catch this type from `runa.errors`; root-module re-export is intentionally forbidden.

## Signature

`ConfigError()`

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-CONFIGERROR` · `TC-091-09`

```python
def config_error(error: ConfigError) -> str:
    return error.message
```

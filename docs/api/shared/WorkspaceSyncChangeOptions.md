# `WorkspaceSyncChangeOptions`

Options for reading ordered committed workspace changes.

## Import

`from cuna import WorkspaceSyncChangeOptions`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncChangeOptions(reader_version: int, cursor: str | None = None, limit: int | None = None)`

## Artifact docstring

Options for reading ordered committed workspace changes.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `reader_version` | `int` | Accepted `reader_version` value defined by the public contract. |
| `cursor` | `str | None` | Accepted `cursor` value defined by the public contract. |
| `limit` | `int | None` | Accepted `limit` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCCHANGEOPTIONS`; `TC-091-09`

```python
def workspace_sync_change_options(value: WorkspaceSyncChangeOptions) -> int:
    return value.reader_version
```

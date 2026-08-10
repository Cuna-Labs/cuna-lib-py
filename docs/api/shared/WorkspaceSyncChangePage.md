# `WorkspaceSyncChangePage`

One bounded page of ordered committed workspace changes.

## Import

`from cuna import WorkspaceSyncChangePage`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncChangePage(selected_protocol: Literal[1, 2], items: tuple[WorkspaceSyncChangeItem, ...], next_cursor: str | None)`

## Artifact docstring

One bounded page of ordered committed workspace changes.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `selected_protocol` | `Literal[1, 2]` | Accepted `selected_protocol` value defined by the public contract. |
| `items` | `tuple[WorkspaceSyncChangeItem, ...]` | Accepted `items` value defined by the public contract. |
| `next_cursor` | `str | None` | Accepted `next_cursor` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCCHANGEPAGE`; `TC-091-09`

```python
def workspace_sync_change_page(value: WorkspaceSyncChangePage) -> int:
    return value.selected_protocol
```

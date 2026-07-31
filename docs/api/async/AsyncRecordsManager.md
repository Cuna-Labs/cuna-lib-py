# `AsyncRecordsManager`

Asynchronous entry point for listing workspace records.

## Import

`from runa import AsyncRecordsManager`

## Acquisition

Obtain this stable instance from `AsyncRuna.records`.

## Signature

`AsyncRecordsManager(client: AsyncRuna, token: object = None)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`list`](#list) | `list() -> list[Record]` | List the resources visible to the authenticated workspace. | `list[Record]` | `ApiError`, `CancelledError` |

<a id="list"></a>
### `list`

List the resources visible to the authenticated workspace.

- Exact shape: `list() -> list[Record]`
- Returns: `list[Record]`
- Raises: `ApiError`, `CancelledError`

## Sync/async pair

See the behaviorally equivalent [`RecordsManager`](../sync/RecordsManager.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ASYNCRECORDSMANAGER` · `TC-091-09`

```python
async def async_records_manager(manager: AsyncRecordsManager) -> None:
    records = await manager.list()
    del records
```

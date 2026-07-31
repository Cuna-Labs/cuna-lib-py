# `RecordsManager`

Synchronous entry point for listing workspace records.

## Import

`from runa import RecordsManager`

## Acquisition

Obtain this stable instance from `Runa.records`.

## Signature

`RecordsManager(client: Runa, token: object = None)`

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`list`](#list) | `list() -> list[Record]` | List the resources visible to the authenticated workspace. | `list[Record]` | `ApiError` |

<a id="list"></a>
### `list`

List the resources visible to the authenticated workspace.

- Exact shape: `list() -> list[Record]`
- Returns: `list[Record]`
- Raises: `ApiError`

## Sync/async pair

See the behaviorally equivalent [`AsyncRecordsManager`](../async/AsyncRecordsManager.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-RECORDSMANAGER` · `TC-091-09`

```python
def records_manager(manager: RecordsManager) -> None:
    records = manager.list()
    del records
```

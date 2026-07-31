# `AsyncRecordsManager`

Stable asynchronous records manager obtained from ``AsyncRuna.records``.

## Import

`from runa import AsyncRecordsManager`

## Acquisition

Obtain this stable instance from `AsyncRuna.records`.

## Signature

`AsyncRecordsManager(client: AsyncRuna, token: object = None)`

## Artifact docstring

Stable asynchronous records manager obtained from ``AsyncRuna.records``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`list`](#list) | `list() -> list[Record]` | List visible records asynchronously. | `list[Record]` | `ApiError`, `CancelledError` |

<a id="list"></a>
### `list`

List visible records asynchronously.

- Exact shape: `list() -> list[Record]`
- Returns: `list[Record]`
- Raises: `ApiError`, `CancelledError`

List visible records asynchronously.

Returns:
    Immutable records in service order.
Raises:
    ApiError: If the request fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCRECORDSMANAGER`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`RecordsManager`](../sync/RecordsManager.md).

## Safe executable example

Source: [`examples/reference.py`](../../../examples/reference.py) · `REF-EX-ASYNCRECORDSMANAGER` · `TC-091-09`

```python
async def async_records_manager(manager: AsyncRecordsManager) -> None:
    records = await manager.list()
    del records
```

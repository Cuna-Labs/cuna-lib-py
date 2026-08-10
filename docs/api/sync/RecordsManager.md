# `RecordsManager`

Stable synchronous records manager; obtain from :attr:`Cuna.records`.

## Import

`from cuna import RecordsManager`

## Acquisition

Obtain this stable instance from `Cuna.records`.

## Signature

`RecordsManager(client: Cuna, token: object = None)`

## Artifact docstring

Stable synchronous records manager; obtain from :attr:`Cuna.records`.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`list`](#list) | `list() -> list[Record]` | List visible records. | `list[Record]` | `ApiError` |

<a id="list"></a>
### `list`

List visible records.

- Exact shape: `list() -> list[Record]`
- Returns: `list[Record]`
- Raises: `ApiError`

List visible records.

Returns:
    Immutable records in service order.
Raises:
    ApiError: If the request fails or the response is malformed.
Examples:
    See ``REF-EX-RECORDSMANAGER`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`AsyncRecordsManager`](../async/AsyncRecordsManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-RECORDSMANAGER`; `TC-091-09`

```python
def records_manager(manager: RecordsManager) -> None:
    records = manager.list()
    del records
```

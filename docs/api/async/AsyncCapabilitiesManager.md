# `AsyncCapabilitiesManager`

Stable asynchronous capability discovery manager.

## Import

`from runa import AsyncCapabilitiesManager`

## Acquisition

Obtain this stable instance from `AsyncRuna.capabilities`.

## Signature

`AsyncCapabilitiesManager(client: AsyncRuna, token: object = None)`

## Artifact docstring

Stable asynchronous capability discovery manager.

Examples:
    See ``REF-EX-ASYNCCAPABILITIESMANAGER`` and ``TC-091-09``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`get`](#get) | `get(scope: CapabilityScope, resource_id: str | None = None) -> CapabilitySnapshot` | Get leased availability evidence without granting authority. | `CapabilitySnapshot` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="get"></a>
### `get`

Get leased availability evidence without granting authority.

- Exact shape: `get(scope: CapabilityScope, resource_id: str | None = None) -> CapabilitySnapshot`
- Returns: `CapabilitySnapshot`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Get leased availability evidence without granting authority.

Args:
    scope: Account, machine, or explicit AgentSession scope.
    resource_id: Required machine or AgentSession UUID; absent for account scope.
Returns:
    A fresh account or machine capability snapshot.
Raises:
    ConfigError: If the scope and resource identifier do not form a valid request.
    ApiError: If discovery fails or the response is malformed.
    asyncio.CancelledError: If the caller cancels the operation.
Examples:
    See ``REF-EX-ASYNCCAPABILITIESMANAGER`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`CapabilitiesManager`](../sync/CapabilitiesManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCCAPABILITIESMANAGER`; `TC-091-09`

```python
async def async_capabilities_manager(manager: AsyncCapabilitiesManager) -> None:
    snapshot = await manager.get(CapabilityScope.ACCOUNT)
    del snapshot
```

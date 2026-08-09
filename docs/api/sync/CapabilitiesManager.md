# `CapabilitiesManager`

Stable synchronous capability discovery manager.

## Import

`from runa import CapabilitiesManager`

## Acquisition

Obtain this stable instance from `Runa.capabilities`.

## Signature

`CapabilitiesManager(client: Runa, token: object = None)`

## Artifact docstring

Stable synchronous capability discovery manager.

Examples:
    See ``REF-EX-CAPABILITIESMANAGER`` and ``TC-091-09``.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`get`](#get) | `get(scope: CapabilityScope, resource_id: str | None = None) -> CapabilitySnapshot` | Get leased availability evidence without granting authority. | `CapabilitySnapshot` | `ConfigError`, `ApiError` |

<a id="get"></a>
### `get`

Get leased availability evidence without granting authority.

- Exact shape: `get(scope: CapabilityScope, resource_id: str | None = None) -> CapabilitySnapshot`
- Returns: `CapabilitySnapshot`
- Raises: `ConfigError`, `ApiError`

Get leased availability evidence without granting authority.

Args:
    scope: Account, machine, or explicit AgentSession scope.
    resource_id: Required machine or AgentSession UUID; absent for account scope.
Returns:
    A fresh account or machine capability snapshot.
Raises:
    ConfigError: If the scope and resource identifier do not form a valid request.
    ApiError: If discovery fails or the response is malformed.
Examples:
    See ``REF-EX-CAPABILITIESMANAGER`` and ``TC-091-09``.

## Sync/async pair

See the behaviorally equivalent [`AsyncCapabilitiesManager`](../async/AsyncCapabilitiesManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-CAPABILITIESMANAGER`; `TC-091-09`

```python
def capabilities_manager(manager: CapabilitiesManager) -> None:
    snapshot = manager.get(CapabilityScope.ACCOUNT)
    del snapshot
```

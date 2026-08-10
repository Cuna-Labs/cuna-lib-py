# `AsyncWorkspaceSyncManager`

Asynchronous explicit bounded workspace synchronization operations.

## Import

`from cuna import AsyncWorkspaceSyncManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`AsyncWorkspaceSyncManager(client: AsyncCuna, token: object = None)`

## Artifact docstring

Asynchronous explicit bounded workspace synchronization operations.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`begin`](#begin) | `begin(workspace_id: str, request: WorkspaceSyncBeginRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncSession]` | Begin one bounded workspace synchronization session asynchronously. | `WorkspaceSyncEnvelope[WorkspaceSyncSession]` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="begin"></a>
### `begin`

Begin one bounded workspace synchronization session asynchronously.

- Exact shape: `begin(workspace_id: str, request: WorkspaceSyncBeginRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncSession]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncSession]`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Begin one bounded workspace synchronization session asynchronously.

| [`negotiate`](#negotiate) | `negotiate(sync_id: str, request: WorkspaceSyncManifestPageRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]` | Negotiate one ordered manifest page asynchronously. | `WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="negotiate"></a>
### `negotiate`

Negotiate one ordered manifest page asynchronously.

- Exact shape: `negotiate(sync_id: str, request: WorkspaceSyncManifestPageRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Negotiate one ordered manifest page asynchronously.

| [`upload_chunk`](#upload_chunk) | `upload_chunk(sync_id: str, digest: str, data: bytes, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]` | Upload one content-addressed workspace chunk asynchronously. | `WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="upload_chunk"></a>
### `upload_chunk`

Upload one content-addressed workspace chunk asynchronously.

- Exact shape: `upload_chunk(sync_id: str, digest: str, data: bytes, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Upload one content-addressed workspace chunk asynchronously.

| [`download_chunk`](#download_chunk) | `download_chunk(sync_id: str, digest: str) -> bytes` | Download one chunk as bytes after strict digest and length verification. | `bytes` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="download_chunk"></a>
### `download_chunk`

Download one chunk as bytes after strict digest and length verification.

- Exact shape: `download_chunk(sync_id: str, digest: str) -> bytes`
- Returns: `bytes`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Download one chunk as bytes after strict digest and length verification.

| [`commit`](#commit) | `commit(sync_id: str, request: WorkspaceSyncCommitRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]` | Commit one complete synchronized workspace generation asynchronously. | `WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="commit"></a>
### `commit`

Commit one complete synchronized workspace generation asynchronously.

- Exact shape: `commit(sync_id: str, request: WorkspaceSyncCommitRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Commit one complete synchronized workspace generation asynchronously.

| [`changes`](#changes) | `changes(sync_id: str, options: WorkspaceSyncChangeOptions) -> WorkspaceSyncEnvelope[WorkspaceSyncChangePage]` | Read one ordered page of committed workspace changes asynchronously. | `WorkspaceSyncEnvelope[WorkspaceSyncChangePage]` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="changes"></a>
### `changes`

Read one ordered page of committed workspace changes asynchronously.

- Exact shape: `changes(sync_id: str, options: WorkspaceSyncChangeOptions) -> WorkspaceSyncEnvelope[WorkspaceSyncChangePage]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncChangePage]`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Read one ordered page of committed workspace changes asynchronously.

| [`reconcile`](#reconcile) | `reconcile(workspace_id: str, request: WorkspaceSyncReconcileRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]` | Reconcile one workspace against an observed local generation asynchronously. | `WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]` | `ConfigError`, `ApiError`, `CancelledError` |

<a id="reconcile"></a>
### `reconcile`

Reconcile one workspace against an observed local generation asynchronously.

- Exact shape: `reconcile(workspace_id: str, request: WorkspaceSyncReconcileRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]`
- Raises: `ConfigError`, `ApiError`, `CancelledError`

Reconcile one workspace against an observed local generation asynchronously.

## Sync/async pair

See the behaviorally equivalent [`WorkspaceSyncManager`](../sync/WorkspaceSyncManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-ASYNCWORKSPACESYNCMANAGER`; `TC-091-09`

```python
async def async_workspace_sync_manager(manager: AsyncWorkspaceSyncManager) -> None:
    del manager
```

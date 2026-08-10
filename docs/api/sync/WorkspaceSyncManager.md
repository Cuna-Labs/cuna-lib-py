# `WorkspaceSyncManager`

Explicit bounded workspace synchronization operations.

## Import

`from runa import WorkspaceSyncManager`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncManager(client: Runa, token: object = None)`

## Artifact docstring

Explicit bounded workspace synchronization operations.

## Public members

| Member | Signature or annotation | Meaning | Returns | Raises |
| --- | --- | --- | --- | --- |
| [`begin`](#begin) | `begin(workspace_id: str, request: WorkspaceSyncBeginRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncSession]` | Begin one bounded workspace synchronization session. | `WorkspaceSyncEnvelope[WorkspaceSyncSession]` | `ConfigError`, `ApiError` |

<a id="begin"></a>
### `begin`

Begin one bounded workspace synchronization session.

- Exact shape: `begin(workspace_id: str, request: WorkspaceSyncBeginRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncSession]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncSession]`
- Raises: `ConfigError`, `ApiError`

Begin one bounded workspace synchronization session.

| [`negotiate`](#negotiate) | `negotiate(sync_id: str, request: WorkspaceSyncManifestPageRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]` | Negotiate one ordered manifest page. | `WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]` | `ConfigError`, `ApiError` |

<a id="negotiate"></a>
### `negotiate`

Negotiate one ordered manifest page.

- Exact shape: `negotiate(sync_id: str, request: WorkspaceSyncManifestPageRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncManifestReceipt]`
- Raises: `ConfigError`, `ApiError`

Negotiate one ordered manifest page.

| [`upload_chunk`](#upload_chunk) | `upload_chunk(sync_id: str, digest: str, data: bytes, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]` | Upload one content-addressed workspace chunk. | `WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]` | `ConfigError`, `ApiError` |

<a id="upload_chunk"></a>
### `upload_chunk`

Upload one content-addressed workspace chunk.

- Exact shape: `upload_chunk(sync_id: str, digest: str, data: bytes, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncChunkReceipt]`
- Raises: `ConfigError`, `ApiError`

Upload one content-addressed workspace chunk.

| [`download_chunk`](#download_chunk) | `download_chunk(sync_id: str, digest: str) -> bytes` | Download one chunk as bytes after strict digest and length verification. | `bytes` | `ConfigError`, `ApiError` |

<a id="download_chunk"></a>
### `download_chunk`

Download one chunk as bytes after strict digest and length verification.

- Exact shape: `download_chunk(sync_id: str, digest: str) -> bytes`
- Returns: `bytes`
- Raises: `ConfigError`, `ApiError`

Download one chunk as bytes after strict digest and length verification.

| [`commit`](#commit) | `commit(sync_id: str, request: WorkspaceSyncCommitRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]` | Commit one complete synchronized workspace generation. | `WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]` | `ConfigError`, `ApiError` |

<a id="commit"></a>
### `commit`

Commit one complete synchronized workspace generation.

- Exact shape: `commit(sync_id: str, request: WorkspaceSyncCommitRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncCommitReceipt]`
- Raises: `ConfigError`, `ApiError`

Commit one complete synchronized workspace generation.

| [`changes`](#changes) | `changes(sync_id: str, options: WorkspaceSyncChangeOptions) -> WorkspaceSyncEnvelope[WorkspaceSyncChangePage]` | Read one ordered page of committed workspace changes. | `WorkspaceSyncEnvelope[WorkspaceSyncChangePage]` | `ConfigError`, `ApiError` |

<a id="changes"></a>
### `changes`

Read one ordered page of committed workspace changes.

- Exact shape: `changes(sync_id: str, options: WorkspaceSyncChangeOptions) -> WorkspaceSyncEnvelope[WorkspaceSyncChangePage]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncChangePage]`
- Raises: `ConfigError`, `ApiError`

Read one ordered page of committed workspace changes.

| [`reconcile`](#reconcile) | `reconcile(workspace_id: str, request: WorkspaceSyncReconcileRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]` | Reconcile one workspace against an observed local generation. | `WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]` | `ConfigError`, `ApiError` |

<a id="reconcile"></a>
### `reconcile`

Reconcile one workspace against an observed local generation.

- Exact shape: `reconcile(workspace_id: str, request: WorkspaceSyncReconcileRequest, idempotency_key: str) -> WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]`
- Returns: `WorkspaceSyncEnvelope[WorkspaceSyncReconcileReceipt]`
- Raises: `ConfigError`, `ApiError`

Reconcile one workspace against an observed local generation.

## Sync/async pair

See the behaviorally equivalent [`AsyncWorkspaceSyncManager`](../async/AsyncWorkspaceSyncManager.md).

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCMANAGER`; `TC-091-09`

```python
def workspace_sync_manager(manager: WorkspaceSyncManager) -> None:
    del manager
```

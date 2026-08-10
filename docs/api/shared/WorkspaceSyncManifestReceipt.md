# `WorkspaceSyncManifestReceipt`

Receipt for one accepted workspace manifest page.

## Import

`from cuna import WorkspaceSyncManifestReceipt`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncManifestReceipt(sync: WorkspaceSyncSession, page_index: int, page_digest: str, missing_digests: tuple[str, ...])`

## Artifact docstring

Receipt for one accepted workspace manifest page.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `sync` | `WorkspaceSyncSession` | Accepted `sync` value defined by the public contract. |
| `page_index` | `int` | Accepted `page_index` value defined by the public contract. |
| `page_digest` | `str` | Accepted `page_digest` value defined by the public contract. |
| `missing_digests` | `tuple[str, ...]` | Accepted `missing_digests` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCMANIFESTRECEIPT`; `TC-091-09`

```python
def workspace_sync_manifest_receipt(value: WorkspaceSyncManifestReceipt) -> str:
    return value.page_digest
```

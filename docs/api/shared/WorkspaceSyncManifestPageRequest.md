# `WorkspaceSyncManifestPageRequest`

One bounded ordered workspace manifest page.

## Import

`from cuna import WorkspaceSyncManifestPageRequest`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncManifestPageRequest(page_index: int, is_last: bool, minimum_reader: int, minimum_writer: int, entries: list[WorkspaceSyncManifestEntry])`

## Artifact docstring

One bounded ordered workspace manifest page.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `page_index` | `int` | Accepted `page_index` value defined by the public contract. |
| `is_last` | `bool` | Accepted `is_last` value defined by the public contract. |
| `minimum_reader` | `int` | Accepted `minimum_reader` value defined by the public contract. |
| `minimum_writer` | `int` | Accepted `minimum_writer` value defined by the public contract. |
| `entries` | `list[WorkspaceSyncManifestEntry]` | Accepted `entries` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCMANIFESTPAGEREQUEST`; `TC-091-09`

```python
def workspace_sync_manifest_page_request(value: WorkspaceSyncManifestPageRequest) -> int:
    return value.page_index
```

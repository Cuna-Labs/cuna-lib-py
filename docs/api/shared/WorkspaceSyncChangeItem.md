# `WorkspaceSyncChangeItem`

One ordered change in a committed workspace generation.

## Import

`from runa import WorkspaceSyncChangeItem`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncChangeItem(generation: int, operation: Literal['revision', 'upsert', 'delete'], path: str | None, entry: WorkspaceSyncManifestEntry | None, manifest_root: str, exclusion_policy_digest: str, committed_at: str, minimum_reader: int, minimum_writer: int)`

## Artifact docstring

One ordered change in a committed workspace generation.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `generation` | `int` | Accepted `generation` value defined by the public contract. |
| `operation` | `Literal['revision', 'upsert', 'delete']` | Accepted `operation` value defined by the public contract. |
| `path` | `str | None` | Accepted `path` value defined by the public contract. |
| `entry` | `WorkspaceSyncManifestEntry | None` | Accepted `entry` value defined by the public contract. |
| `manifest_root` | `str` | Accepted `manifest_root` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |
| `committed_at` | `str` | Accepted `committed_at` value defined by the public contract. |
| `minimum_reader` | `int` | Accepted `minimum_reader` value defined by the public contract. |
| `minimum_writer` | `int` | Accepted `minimum_writer` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCCHANGEITEM`; `TC-091-09`

```python
def workspace_sync_change_item(value: WorkspaceSyncChangeItem) -> int:
    return value.generation
```

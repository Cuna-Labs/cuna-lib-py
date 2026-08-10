# `WorkspaceSyncManifestEntry`

Portable manifest entry for one workspace path.

## Import

`from runa import WorkspaceSyncManifestEntry`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncManifestEntry(path: str, kind: Literal['directory', 'file', 'symlink'], byte_length: int, executable: bool, chunks: list[WorkspaceSyncChunkRef], link_target: str | None)`

## Artifact docstring

Portable manifest entry for one workspace path.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `path` | `str` | Accepted `path` value defined by the public contract. |
| `kind` | `Literal['directory', 'file', 'symlink']` | Record kind discriminator. |
| `byte_length` | `int` | Accepted `byte_length` value defined by the public contract. |
| `executable` | `bool` | Accepted `executable` value defined by the public contract. |
| `chunks` | `list[WorkspaceSyncChunkRef]` | Accepted `chunks` value defined by the public contract. |
| `link_target` | `str | None` | Accepted `link_target` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCMANIFESTENTRY`; `TC-091-09`

```python
def workspace_sync_manifest_entry(value: WorkspaceSyncManifestEntry) -> str:
    return value.path
```

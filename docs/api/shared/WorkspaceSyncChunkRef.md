# `WorkspaceSyncChunkRef`

Content-addressed reference to one bounded workspace chunk.

## Import

`from cuna import WorkspaceSyncChunkRef`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncChunkRef(digest: str, byte_length: int)`

## Artifact docstring

Content-addressed reference to one bounded workspace chunk.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `digest` | `str` | Accepted `digest` value defined by the public contract. |
| `byte_length` | `int` | Accepted `byte_length` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCCHUNKREF`; `TC-091-09`

```python
def workspace_sync_chunk_ref(value: WorkspaceSyncChunkRef) -> str:
    return value.digest
```

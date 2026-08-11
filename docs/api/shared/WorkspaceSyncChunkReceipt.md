# `WorkspaceSyncChunkReceipt`

Receipt for one verified content-addressed workspace chunk.

## Import

`from cuna import WorkspaceSyncChunkReceipt`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncChunkReceipt(selected_protocol: Literal[1, 2], digest: str, byte_length: int, stored: bool)`

## Artifact docstring

Receipt for one verified content-addressed workspace chunk.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `selected_protocol` | `Literal[1, 2]` | Accepted `selected_protocol` value defined by the public contract. |
| `digest` | `str` | Accepted `digest` value defined by the public contract. |
| `byte_length` | `int` | Accepted `byte_length` value defined by the public contract. |
| `stored` | `bool` | Accepted `stored` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCCHUNKRECEIPT`; `TC-091-09`

```python
def workspace_sync_chunk_receipt(value: WorkspaceSyncChunkReceipt) -> str:
    return value.digest
```

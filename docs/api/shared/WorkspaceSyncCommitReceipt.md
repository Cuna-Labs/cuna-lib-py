# `WorkspaceSyncCommitReceipt`

Receipt for one atomically committed workspace generation.

## Import

`from runa import WorkspaceSyncCommitReceipt`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncCommitReceipt(selected_protocol: Literal[1, 2], state: Literal['committed'], generation: int, manifest_root: str, committed_at: str, minimum_reader: int, minimum_writer: int)`

## Artifact docstring

Receipt for one atomically committed workspace generation.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `selected_protocol` | `Literal[1, 2]` | Accepted `selected_protocol` value defined by the public contract. |
| `state` | `Literal['committed']` | Strict secret-free authentication state of the session agent. |
| `generation` | `int` | Accepted `generation` value defined by the public contract. |
| `manifest_root` | `str` | Accepted `manifest_root` value defined by the public contract. |
| `committed_at` | `str` | Accepted `committed_at` value defined by the public contract. |
| `minimum_reader` | `int` | Accepted `minimum_reader` value defined by the public contract. |
| `minimum_writer` | `int` | Accepted `minimum_writer` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCCOMMITRECEIPT`; `TC-091-09`

```python
def workspace_sync_commit_receipt(value: WorkspaceSyncCommitReceipt) -> int:
    return value.generation
```

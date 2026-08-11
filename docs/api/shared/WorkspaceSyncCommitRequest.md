# `WorkspaceSyncCommitRequest`

Request to atomically commit a synchronized workspace generation.

## Import

`from cuna import WorkspaceSyncCommitRequest`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncCommitRequest(expected_generation: int, exclusion_policy_digest: str, manifest_root: str, minimum_reader: int, minimum_writer: int)`

## Artifact docstring

Request to atomically commit a synchronized workspace generation.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `expected_generation` | `int` | Accepted `expected_generation` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |
| `manifest_root` | `str` | Accepted `manifest_root` value defined by the public contract. |
| `minimum_reader` | `int` | Accepted `minimum_reader` value defined by the public contract. |
| `minimum_writer` | `int` | Accepted `minimum_writer` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCCOMMITREQUEST`; `TC-091-09`

```python
def workspace_sync_commit_request(value: WorkspaceSyncCommitRequest) -> int:
    return value.expected_generation
```

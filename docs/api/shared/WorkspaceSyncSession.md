# `WorkspaceSyncSession`

Observed state of one bounded workspace synchronization session.

## Import

`from cuna import WorkspaceSyncSession`

## Acquisition

Import the canonical value from the root module as shown above.

## Signature

`WorkspaceSyncSession(id: str, workspace_id: str, machine_id: str, base_generation: int, exclusion_policy_digest: str, selected_protocol: Literal[1, 2], capabilities: tuple[WorkspaceSyncCapability, ...], state: Literal['staging', 'committed', 'conflicted', 'expired'], manifest_entry_count: int, manifest_encoded_bytes: int, content_bytes: int, expires_at: str, created_at: str, updated_at: str, last_page_index: int | None = None, committed_generation: int | None = None, committed_manifest_root: str | None = None)`

## Artifact docstring

Observed state of one bounded workspace synchronization session.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `id` | `str` | Canonical identifier. |
| `workspace_id` | `str` | Accepted `workspace_id` value defined by the public contract. |
| `machine_id` | `str` | Accepted `machine_id` value defined by the public contract. |
| `base_generation` | `int` | Accepted `base_generation` value defined by the public contract. |
| `exclusion_policy_digest` | `str` | Accepted `exclusion_policy_digest` value defined by the public contract. |
| `selected_protocol` | `Literal[1, 2]` | Accepted `selected_protocol` value defined by the public contract. |
| `capabilities` | `tuple[WorkspaceSyncCapability, ...]` | Ordered capability descriptions. |
| `state` | `Literal['staging', 'committed', 'conflicted', 'expired']` | Strict secret-free authentication state of the session agent. |
| `manifest_entry_count` | `int` | Accepted `manifest_entry_count` value defined by the public contract. |
| `manifest_encoded_bytes` | `int` | Accepted `manifest_encoded_bytes` value defined by the public contract. |
| `content_bytes` | `int` | Accepted `content_bytes` value defined by the public contract. |
| `expires_at` | `str` | RFC 3339 evidence expiry timestamp. |
| `created_at` | `str` | Service timestamp encoded as an RFC 3339 string. |
| `updated_at` | `str` | Service timestamp encoded as an RFC 3339 string. |
| `last_page_index` | `int | None` | Accepted `last_page_index` value defined by the public contract. |
| `committed_generation` | `int | None` | Accepted `committed_generation` value defined by the public contract. |
| `committed_manifest_root` | `str | None` | Accepted `committed_manifest_root` value defined by the public contract. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCSESSION`; `TC-091-09`

```python
def workspace_sync_session(value: WorkspaceSyncSession) -> str:
    return value.id
```

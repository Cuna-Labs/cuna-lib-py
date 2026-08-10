# `WorkspaceSyncProblem`

Validated negotiated workspace-sync failure with protocol evidence.

## Import

`from cuna.errors import WorkspaceSyncProblem`

## Acquisition

Catch this type from `cuna.errors`; root-module re-export is intentionally forbidden.

## Signature

`WorkspaceSyncProblem(type: str, title: str, status: int, code: str, request_id: str, retryable: bool, detail: str | None = None, action: ProblemAction | None = None, selected_protocol: Literal[1, 2] | None = None, capabilities: tuple[WorkspaceSyncCapability, ...] = ())`

## Artifact docstring

Validated negotiated workspace-sync failure with protocol evidence.

## Fields and values

| Name | Annotation | Optionality and meaning |
| --- | --- | --- |
| `selected_protocol` | `Literal[1, 2] | None` | Accepted `selected_protocol` value defined by the public contract. |
| `capabilities` | `tuple[WorkspaceSyncCapability, ...]` | Ordered capability descriptions. |

## Safe executable example

Source: [`docs/reference/examples.py`](../../reference/examples.py); `REF-EX-WORKSPACESYNCPROBLEM`; `TC-091-09`

```python
def workspace_sync_problem(error: WorkspaceSyncProblem) -> int | None:
    return error.selected_protocol
```

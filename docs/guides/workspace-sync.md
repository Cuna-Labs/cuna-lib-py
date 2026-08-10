# Workspace bindings and synchronization

Workspace synchronization uses two deliberately different identities:

- `workspace_id` is the public workspace in the API route.
- `workspace_binding_id` identifies the canonical binding between a local project and a machine.

Never substitute one for the other. The SDK rejects identical values locally, and Cuna verifies
the complete binding identity again before accepting a synchronization effect.

Create or exactly adopt a binding with a caller-stable idempotency key:

```python
from cuna import Cuna, WorkspaceBindingCreateRequest

with Cuna() as client:
    binding = client.workspace_bindings.create(
        WorkspaceBindingCreateRequest(
            workspace_id=workspace_id,
            project_id=project_id,
            local_instance_id=local_instance_id,
            machine_id=machine_id,
            exclusion_policy_digest=policy_digest,
            excluded_prefixes=[".git", "node_modules"],
        ),
        idempotency_key="binding-create-project-a",
    )
```

Pass `binding.binding_id` in both `WorkspaceSyncBeginRequest` and
`WorkspaceSyncReconcileRequest`. The remaining bounded workflow is:

1. `client.workspace_sync.begin(...)`
2. `client.workspace_sync.negotiate(...)` for each manifest page
3. `client.workspace_sync.upload_chunk(...)` for each missing digest
4. `client.workspace_sync.download_chunk(...)` for content referenced by remote changes
5. `client.workspace_sync.commit(...)`
6. `client.workspace_sync.changes(...)` for ordered remote changes
7. `client.workspace_sync.reconcile(...)` when convergence must be checked explicitly

`download_chunk` returns verified `bytes`, not a base64 envelope. Before returning content, the
SDK requires canonical base64, the declared byte length, the requested digest, and the computed
SHA-256 digest to agree. Treat a malformed-response error as an integrity failure; do not use
partial or unverified content.

Every mutating operation requires a caller-stable `Idempotency-Key`. Reuse the same key only for
an exact replay of the same operation and body. Do not log binding requests, manifest content, or
problem details indiscriminately.

Successful responses expose typed receipt models. A workspace-sync API failure may expose a
`WorkspaceSyncProblem` through `ApiError.problem`; its `selected_protocol` and `capabilities`
fields are validated together and are never inferred when the server could not select a protocol.
The asynchronous client exposes the same managers and models with awaited methods.

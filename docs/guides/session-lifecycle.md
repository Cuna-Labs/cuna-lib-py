# Session lifecycle

Use the existing handle as shown by
[`examples/sync_lifecycle.py`](../../examples/sync_lifecycle.py) and
[`examples/async_lifecycle.py`](../../examples/async_lifecycle.py). `refresh()` is a direct UUID
item read using `GET /v1/sessions/{session_id}`. The service owns transition legality; the SDK does
not predict readiness or poll. Deletion returns an acknowledgement and does not promise a cached
snapshot change. See the [API reference](../api/README.md).

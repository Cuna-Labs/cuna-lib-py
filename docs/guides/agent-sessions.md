# Agent sessions

`client.agent_sessions` provides synchronous and asynchronous list, create, get, rename,
and terminate operations for durable agent-process intent on a Runa machine. Returned
models are frozen. `process_state == UNKNOWN` is not proof that no process exists, and a
successful termination request does not assert immediate process absence.

Creation requires a stable `idempotency_key`, an agent, and a `/workspace` working
directory. Claude Code and Codex default to interactive login. OpenClaw defaults to a
credential binding and therefore requires `credential_binding_id`. Pagination cursors are
opaque and should only be replayed to `list`.

See `examples/sync_agent_sessions.py` and `examples/async_agent_sessions.py`. This surface
does not open a PTY, perform provider login, or synchronize local files.

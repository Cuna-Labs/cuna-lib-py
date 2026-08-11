# Agent sessions

`client.agent_sessions` provides synchronous and asynchronous list, create, get, rename,
terminate, and terminal-connection grant operations for durable agent-process intent on a
Cuna machine. Returned
models are frozen. `process_state == UNKNOWN` is not proof that no process exists, and a
successful termination request does not assert immediate process absence.

Creation requires a stable `idempotency_key`, an agent, a `/workspace` working directory,
and the exact `workspace_binding_id` plus committed `workspace_generation` produced by Cuna
workspace synchronization. Cuna binds these values immutably to the new session; read and
list may omit both only for sessions created before this authority existed. Claude Code
and Codex default to interactive login. OpenClaw defaults to a
credential binding and therefore requires `credential_binding_id`. Pagination cursors are
opaque and should only be replayed to `list`.

See `examples/sync_agent_sessions.py` and `examples/async_agent_sessions.py`. This surface
does not open a PTY, perform provider login, or synchronize local files.

To let a separate terminal client connect, call `create_terminal_connection` with the
AgentSession ID and a caller-stable idempotency key. The result is short-lived metadata:
the stream URL, one-use token, resume handle, protocol, five explicit capability records,
and expiry. Treat `connect_token` as a secret. The SDK intentionally does not open the
WebSocket, consume the token, own a PTY/TUI, access a keychain, or synchronize files.

```python
from cuna import TerminalConnectionCreateOptions

grant = client.agent_sessions.create_terminal_connection(
    agent_session.id,
    TerminalConnectionCreateOptions(
        idempotency_key="terminal-connect-018f2a38",
        client_instance_id="desktop.example:1",
    ),
)
```

# Interactive agent login

Claude Code and Codex can use the user's provider subscription through an
interactive login. The SDK does not accept or embed a provider API key for this
flow and does not send console-only provisioning controls.

```python
import time

from cuna import SessionAgent, SessionCreateOptions, SessionStatus

session = client.sessions.create(
    "interactive",
    SessionCreateOptions(agent=SessionAgent.CLAUDE_CODE),
)
while session.snapshot.status is SessionStatus.CREATING:
    time.sleep(2)
    session.refresh()

handoff = session.open()
# Open handoff.url for the user. Never log, persist, or prefetch it.
```

Creation can return `CREATING`; `refresh()` is the supported polling mechanism.
The asynchronous client exposes the same flow with awaited calls and
`asyncio.sleep`.

Synchronous creation can legitimately use the platform's 25-minute durable
provisioning lease and its five-minute recovery window. The SDK therefore
allows 31 minutes for `sessions.create` before timing out. Prefer the default
background flow for interactive agents so callers receive a session handle
immediately.

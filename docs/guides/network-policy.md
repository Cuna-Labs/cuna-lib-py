# Network policy

Choose one outbound policy when creating a session:

```python
from runa import OutboundPolicy, OutboundPolicyMode, SessionCreateOptions

options = SessionCreateOptions(
    outbound_policy=OutboundPolicy(
        OutboundPolicyMode.ALLOWLIST,
        ["api.example.com", "*.assets.example.com"],
    )
)
session = client.sessions.create("restricted", options)
```

`ALLOWLIST` permits only the listed work destinations. `DENYLIST` blocks the
listed destinations and permits other work destinations. Rules are lowercase
exact domains or leading wildcards such as `*.example.com`; ports, paths, URLs,
IP addresses, duplicates, and more than 128 rules are rejected.

Empty lists are meaningful: an empty deny list permits all work destinations,
and an empty allow list permits none. Runa maintains required platform
connectivity internally without exposing its control domains or provider fields.

`allowed_hosts` is the legacy allow-list option. It remains supported for
compatibility, but a request containing both options is rejected locally.

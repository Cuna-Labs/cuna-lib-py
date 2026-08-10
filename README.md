# Cuna Python SDK

Typed synchronous and asynchronous clients from Cuna Labs.

Documentation and support are available at [getcuna.com](https://getcuna.com),
[getcuna.com/docs](https://getcuna.com/docs), and
[getcuna.com/support](https://getcuna.com/support).

## Install

```console
python -m pip install cuna-sdk
```

Set canonical `CUNA_API_KEY` in the process environment. The canonical API origin is
`https://api.getcuna.com`; the historical `https://api.runacode.io` origin
remains accepted for compatibility. Never place credentials in source,
examples, or logs.

## First session

The canonical executable source is
[`examples/sync_first_session.py`](examples/sync_first_session.py), region
`docs:sync-first-session`.

```python
from cuna import Cuna, SessionCreateOptions

with Cuna() as client:
    session = client.sessions.create("first-session", SessionCreateOptions())
    try:
        result = session.exec(["python", "--version"])
        succeeded = result.exit_code == 0
    finally:
        session.delete()
```

## Configuration

Every setting resolves from the first source that is **present**, and a present
but invalid value fails immediately instead of falling through to the next one.

| Setting | Order of resolution |
| --- | --- |
| API key | the `api_key=` argument, then `CUNA_API_KEY` then `RUNA_API_KEY`, then the `api_key` field of `config_file` |
| API origin | the `base_url=` argument, then `CUNA_BASE_URL` then `RUNA_BASE_URL`, then the `base_url` field of `config_file`, then `https://api.getcuna.com` |

Both brand spellings of a variable are accepted. **When both are set the
canonical `CUNA_` name wins and the `RUNA_` name is ignored**, whatever it
holds; unset the canonical name to let the legacy one take effect. Only
`https://api.getcuna.com` and `https://api.runacode.io` are accepted origins:
any other value raises `ConfigError` and is never silently replaced by the
default.

`cuna-sdk` also ships the legacy `runa` namespace. Existing
`from runa import Runa` consumers continue to work, while new code can use
`from cuna import Cuna`. Canonical keys use `cuna_sk_`. The legacy
`RUNA_API_KEY`, `runa_sk_*` key prefix, and wire protocol names are
intentionally retained. A present invalid canonical variable never falls back
to its legacy alias. `api.runacode.io`
remains a legacy-compatible origin while new clients default to
`api.getcuna.com`.

See the [guide index](docs/guides/index.md), [API reference status](docs/api/README.md),
[synchronous first-session source](examples/sync_first_session.py),
[asynchronous first-session source](examples/async_first_session.py),
[error guide](docs/guides/errors-and-cleanup.md),
[troubleshooting](docs/guides/troubleshooting.md), [security policy](SECURITY.md), and
[contribution guide](CONTRIBUTING.md).

Session creation supports explicit allow-list and deny-list outbound policies.
See the [network policy guide](docs/guides/network-policy.md). The legacy
`allowed_hosts` option remains supported but cannot be combined with
`outbound_policy`.

The public SDK create request never sends console-only provisioning controls.
If the API returns `SessionStatus.CREATING`, poll `refresh()` until the machine
is ready. Use `session.open()` only when the application needs a short-lived
terminal handoff; never log, persist, or prefetch the returned URL.

Use `client.agent_sessions` to list, create, read, rename, and request termination
of durable agent-process resources. See the [AgentSession guide](docs/guides/agent-sessions.md).

Use `client.workspace_bindings` to create or resolve the canonical local-project binding and
`client.workspace_sync` for bounded manifest, chunk, commit, change, and reconciliation
operations. Public workspace IDs and binding IDs are separate identities. See the
[workspace synchronization guide](docs/guides/workspace-sync.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).

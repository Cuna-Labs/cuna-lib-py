# Runa Python SDK

Typed synchronous and asynchronous clients for the Runa API.

## Install

```console
python -m pip install runa-sdk
```

Set `RUNA_API_KEY` in the process environment. The default API origin is
`https://api.runacode.io`; never place credentials in source, examples, or logs.

## First session

The canonical executable source is
[`examples/sync_first_session.py`](examples/sync_first_session.py), region
`docs:sync-first-session`.

```python
from runa import Runa, SessionCreateOptions

with Runa() as client:
    session = client.sessions.create("first-session", SessionCreateOptions())
    try:
        result = session.exec(["python", "--version"])
        succeeded = result.exit_code == 0
    finally:
        session.delete()
```

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

Call `session.authentication_status()` (or await the asynchronous equivalent)
to read only the selected agent, authentication method, and strict state. If it
reports `LOGIN_REQUIRED`, use `session.open()` for the user's terminal handoff;
the status response never contains terminal output, account identity, or secrets.

## License

Apache License 2.0. See [LICENSE](LICENSE).

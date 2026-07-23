<div align="center">

# runa-sdk

**The Python SDK for Runa — give agents the work, never the keys.**

</div>

---

Create Runa sessions, run commands inside them, checkpoint their work, and read
the record — from Python, sync or async.

Runa exposes a REST API at `https://api.runacode.io`. This package is a small,
typed wrapper around it, so you can write:

```python
from runa import Runa

runa = Runa()  # reads RUNA_API_KEY from the environment

session = runa.sessions.create(name="hello", agent="claude-code")
try:
    result = session.exec("echo hello from runa")
    print(result.stdout_text)
finally:
    session.delete()
```

An async client (`AsyncRuna`) mirrors the same surface.

## Status

Early development. This repository is being built from the product requirements
documents in the workspace `prds/` folder. The public API is not yet stable.

## Authentication

Set a Runa API key:

```bash
export RUNA_API_KEY="runa_sk_..."
```

Requests go to `https://api.runacode.io` by default; override with
`Runa(base_url="...")` or `RUNA_BASE_URL`. Never commit a real key.

## Install

```bash
pip install runa-sdk
```

## License

TODO — to be decided before the first public release.

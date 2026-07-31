# Synchronous first session

Install with `python -m pip install runa-sdk`, set `RUNA_API_KEY`, and keep the default
`https://api.runacode.io` origin unless your Runa deployment specifies another origin.

Run [`examples/sync_first_session.py`](../../examples/sync_first_session.py), region
`docs:sync-first-session`. It uses `with Runa()`, creates one session with
`SessionCreateOptions()`, receives one buffered exec result, observes only its exit category, and
attempts one deletion in `finally` without masking the primary failure.

Complete signatures belong to the [API reference](../api/README.md).

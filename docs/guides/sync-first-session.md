# Synchronous first session

Install with `python -m pip install cuna-sdk`, set `CUNA_API_KEY`, and keep the canonical
`https://api.getcuna.com` origin. The historical `https://api.runacode.io` origin remains
accepted; the SDK rejects every other selected origin before network I/O.

Run [`examples/sync_first_session.py`](../../examples/sync_first_session.py), region
`docs:sync-first-session`. It uses `with Cuna()`, creates one session with
`SessionCreateOptions()`, receives one buffered exec result, observes only its exit category, and
attempts one deletion in `finally` without masking the primary failure.

Complete signatures belong to the [API reference](../api/README.md).

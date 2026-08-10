# Asynchronous first session

Install with `python -m pip install cuna-sdk`, set `CUNA_API_KEY`, and use the canonical
`https://api.getcuna.com` origin. The historical `https://api.runacode.io` origin remains
accepted for compatibility.

Run [`examples/async_first_session.py`](../../examples/async_first_session.py), region
`docs:async-first-session`. It uses native `async with` and `await`, and attempts exactly one
deletion after successful creation. Complete signatures belong to the
[API reference](../api/README.md).

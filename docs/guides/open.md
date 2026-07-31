# Open

[`examples/sync_open.py`](../../examples/sync_open.py) and
[`examples/async_open.py`](../../examples/async_open.py) explicitly acquire an unrendered
`OpenSessionResult`. Its URL is a service-issued, single-use 60-second capability. Do not print,
log, persist, fetch, navigate to, display, cache, reuse, or test it. Make a new explicit open call
for later acquisition. See the [API reference](../api/README.md).

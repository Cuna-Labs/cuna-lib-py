# Troubleshooting

- Missing or invalid configuration: check canonical `CUNA_API_KEY` without displaying it. A present invalid canonical value does not fall back to legacy `RUNA_API_KEY`.
- Requests reaching the wrong origin: the API origin resolves from `CUNA_BASE_URL` then `RUNA_BASE_URL`, and the API key from `CUNA_API_KEY` then `RUNA_API_KEY`. The first name that is *set* wins even when the other holds a valid value, so unset the canonical name to let the legacy one take effect. An unaccepted origin raises `ConfigError`; it is never silently replaced by the default.
- Closed client: create a new client context; do not reuse a closed instance.
- Lookup ambiguity or not-found: retain the native category and use an exact lowercase UUID.
- API failure: branch on the safe error type/code, never response or exception text.
- Non-zero exec: inspect the structured exit category; it is not automatically an SDK exception.
- Cancellation: preserve native `asyncio.CancelledError` and perform one cleanup attempt.
- Session open: acquire a fresh result and follow the [open safety rules](open.md).

See [errors and cleanup](errors-and-cleanup.md) and the [API reference](../api/README.md).

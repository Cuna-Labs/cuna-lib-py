# Errors and cleanup

The accepted error types are `CunaError`, `ConfigError`, `ApiError`, and `CommandError` from
`cuna.errors`; local lookup outcomes and native async cancellation remain native. Keep the
original exception primary and attempt cleanup once in `finally`, as demonstrated by the two
[first-session guides](index.md). Never render untrusted exception text, response content,
credentials, commands, output, identifiers, email values, or capability URLs.

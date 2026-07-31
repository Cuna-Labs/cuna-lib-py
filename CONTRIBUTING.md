# Contributing

## Branches

- `main` is released, deployable truth.
- `develop/sdk-foundation` is integration. Feature branches merge there before release.

## Ground rules

- Use English in code, comments, documentation, and commit messages.
- The SDK talks only to the Runa endpoint (`https://api.runacode.io` by default).
  It must never reach a non-Runa provider directly or print an API key.
- Every behavior must trace to its accepted product requirement and canonical contract.
- Run formatting, lint, strict typing, tests, package checks, and security gates before review.
- Do not manually edit generated contract files.

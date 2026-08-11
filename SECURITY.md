# Security Policy

## Reporting a vulnerability

Do not open a public issue for security problems. Email
**contact@getcuna.com** with a description and, if possible, a minimal
reproduction. We aim to acknowledge within 72 hours.

## Scope

This SDK is a thin client over the Cuna REST API. Report here anything that
could expose a user's Cuna API key, leak credentials into logs or errors, or
let the SDK reach a host other than the configured Cuna endpoint. Issues in the
Cuna service itself are handled separately — say so in your report and we will
route it.

## Handling secrets

Never include a real `runa_sk_` key in an issue, PR, log, or test fixture.

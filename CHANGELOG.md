# Changelog

## 0.1.0 - Unreleased

SemVer class: initial minor release.

- Additions: expose background session creation, default interactive Claude Code and Codex sessions to background provisioning, document refresh-based readiness polling, and expose short-lived AgentSession terminal connection metadata with typed Problem errors.
- Fixes: give `authentication_status()` a dedicated 30-second attempt timeout without increasing the timeout of unrelated reads.
- Deprecations: none.
- Removals: none.

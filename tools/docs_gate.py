"""Static, fail-closed guide inventory and safety gate."""

from __future__ import annotations

import ast
from pathlib import Path

GUIDES = {
    "index.md",
    "sync-first-session.md",
    "async-first-session.md",
    "session-lifecycle.md",
    "interactive-agent-login.md",
    "agent-sessions.md",
    "network-policy.md",
    "exec.md",
    "checkpoint.md",
    "open.md",
    "records-and-me.md",
    "errors-and-cleanup.md",
    "troubleshooting.md",
}
EXAMPLES = {
    f"{mode}_{topic}.py"
    for mode in ("sync", "async")
    for topic in (
        "first_session",
        "lifecycle",
        "exec",
        "checkpoint",
        "open",
        "records_and_me",
    )
}
EXAMPLES.update({"sync_agent_sessions.py", "async_agent_sessions.py"})


def main() -> int:
    guide_root = Path("docs/guides")
    example_root = Path("examples")
    if {path.name for path in guide_root.glob("*.md")} != GUIDES:
        raise SystemExit("R-092-01: guide inventory mismatch")
    if {path.name for path in example_root.glob("*.py")} != EXAMPLES:
        raise SystemExit("R-092-01: example inventory mismatch")
    for path in sorted(example_root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id
                in {
                    "print",
                    "open",
                }
            ):
                raise SystemExit("R-092-15: unsafe example call")
    print('{"requirement":"R-092-01","verdict":"pass"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Receive one buffered synchronous command result."""

from runa import ExecOptions, Runa

with Runa() as client:
    session = client.sessions.get("00000000-0000-0000-0000-000000000000")
    result = session.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    succeeded = result.exit_code == 0

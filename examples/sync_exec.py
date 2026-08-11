"""Receive one buffered synchronous command result."""

from cuna import Cuna, ExecOptions

with Cuna() as client:
    session = client.sessions.get("00000000-0000-0000-0000-000000000000")
    result = session.exec(["python", "--version"], ExecOptions(timeout_secs=30))
    succeeded = result.exit_code == 0

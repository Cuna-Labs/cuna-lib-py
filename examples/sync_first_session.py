"""Create, use, and clean up one session synchronously."""

from cuna import Cuna, SessionCreateOptions

# [docs:sync-first-session]
with Cuna() as client:
    session = client.sessions.create("first-session", SessionCreateOptions())
    try:
        result = session.exec(["python", "--version"])
        succeeded = result.exit_code == 0
    finally:
        session.delete()
# [docs:sync-first-session]

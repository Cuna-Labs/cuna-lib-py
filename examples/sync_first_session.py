"""Create, use, and clean up one session synchronously."""

from runa import Runa, SessionCreateOptions

# [docs:sync-first-session]
with Runa() as client:
    session = client.sessions.create("first-session", SessionCreateOptions())
    try:
        result = session.exec(["python", "--version"])
        succeeded = result.exit_code == 0
    finally:
        session.delete()
# [docs:sync-first-session]

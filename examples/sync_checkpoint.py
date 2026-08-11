"""Request one named checkpoint acknowledgement."""

from cuna import Cuna

with Cuna() as client:
    session = client.sessions.get("00000000-0000-0000-0000-000000000000")
    acknowledgement = session.checkpoint("before-change")

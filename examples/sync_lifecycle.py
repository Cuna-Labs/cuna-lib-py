"""Use the synchronous lifecycle surface without predicting service state."""

from cuna import Cuna

with Cuna() as client:
    session = client.sessions.get("00000000-0000-0000-0000-000000000000")
    session.refresh()
    session.start()
    session.pause()
    session.resume()
    session.stop()
    session.delete()

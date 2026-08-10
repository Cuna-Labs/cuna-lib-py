"""Acquire an open result without rendering or retaining its URL."""

from cuna import Cuna

with Cuna() as client:
    session = client.sessions.get("00000000-0000-0000-0000-000000000000")
    open_result = session.open()

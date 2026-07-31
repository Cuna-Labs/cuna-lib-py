"""Read the unpaged record collection and caller profile."""

from runa import Runa

with Runa() as client:
    records = client.records.list()
    profile = client.me()

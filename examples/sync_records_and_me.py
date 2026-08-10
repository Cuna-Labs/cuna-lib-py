"""Read the unpaged record collection and caller profile."""

from cuna import Cuna

with Cuna() as client:
    records = client.records.list()
    profile = client.me()

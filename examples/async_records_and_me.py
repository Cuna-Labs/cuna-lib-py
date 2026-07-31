"""Read records and caller profile asynchronously."""

import asyncio

from runa import AsyncRuna


async def main() -> None:
    async with AsyncRuna() as client:
        _records = await client.records.list()
        _profile = await client.me()


asyncio.run(main())

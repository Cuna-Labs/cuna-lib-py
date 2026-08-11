"""Read records and caller profile asynchronously."""

import asyncio

from cuna import AsyncCuna


async def main() -> None:
    async with AsyncCuna() as client:
        _records = await client.records.list()
        _profile = await client.me()


asyncio.run(main())

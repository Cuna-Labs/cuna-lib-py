"""Request one named checkpoint acknowledgement asynchronously."""

import asyncio

from cuna import AsyncCuna


async def main() -> None:
    async with AsyncCuna() as client:
        session = await client.sessions.get("00000000-0000-0000-0000-000000000000")
        _acknowledgement = await session.checkpoint("before-change")


asyncio.run(main())

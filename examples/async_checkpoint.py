"""Request one named checkpoint acknowledgement asynchronously."""

import asyncio

from runa import AsyncRuna


async def main() -> None:
    async with AsyncRuna() as client:
        session = await client.sessions.get("00000000-0000-0000-0000-000000000000")
        acknowledgement = await session.checkpoint("before-change")


asyncio.run(main())

"""Use the native asynchronous lifecycle surface."""

import asyncio

from runa import AsyncRuna


async def main() -> None:
    async with AsyncRuna() as client:
        session = await client.sessions.get("00000000-0000-0000-0000-000000000000")
        await session.refresh()
        await session.start()
        await session.pause()
        await session.resume()
        await session.stop()
        await session.delete()


asyncio.run(main())

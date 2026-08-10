"""Acquire an open result asynchronously without rendering or retaining its URL."""

import asyncio

from cuna import AsyncCuna


async def main() -> None:
    async with AsyncCuna() as client:
        session = await client.sessions.get("00000000-0000-0000-0000-000000000000")
        _open_result = await session.open()


asyncio.run(main())

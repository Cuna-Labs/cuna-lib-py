"""Create, use, and clean up one session asynchronously."""

import asyncio

from cuna import AsyncCuna, SessionCreateOptions


async def main() -> None:
    # [docs:async-first-session]
    async with AsyncCuna() as client:
        session = await client.sessions.create("first-session", SessionCreateOptions())
        try:
            result = await session.exec(["python", "--version"])
            _succeeded = result.exit_code == 0
        finally:
            await session.delete()
    # [docs:async-first-session]


asyncio.run(main())

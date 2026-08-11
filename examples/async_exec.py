"""Receive one buffered asynchronous command result."""

import asyncio

from cuna import AsyncCuna, ExecOptions


async def main() -> None:
    async with AsyncCuna() as client:
        session = await client.sessions.get("00000000-0000-0000-0000-000000000000")
        result = await session.exec(["python", "--version"], ExecOptions(timeout_secs=30))
        _succeeded = result.exit_code == 0


asyncio.run(main())

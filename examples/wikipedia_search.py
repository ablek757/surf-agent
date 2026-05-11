"""Programmatic example: search Wikipedia and summarize the result."""

from __future__ import annotations

import asyncio

from surf_agent import SurfAgent


async def main() -> None:
    agent = SurfAgent()
    result = await agent.run(
        task="Search Wikipedia for 'Playwright (software)' and tell me which company maintains it.",
        start_url="https://www.wikipedia.org",
    )
    print("ANSWER:", result.answer)
    print("STEPS :", result.steps_taken)


if __name__ == "__main__":
    asyncio.run(main())

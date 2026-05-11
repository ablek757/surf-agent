"""Browser controller — thin wrapper around Playwright that executes an `Action`."""

from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .actions import (
    Action,
    BackAction,
    ClickAction,
    GotoAction,
    ScreenshotAction,
    ScrollAction,
    TypeAction,
    WaitAction,
)
from .config import Config
from .dom import PageSnapshot, locator_selector, snapshot_page


class BrowserController:
    def __init__(self, page: Page, snapshot: PageSnapshot | None = None) -> None:
        self.page = page
        self._snapshot = snapshot

    @property
    def snapshot(self) -> PageSnapshot | None:
        return self._snapshot

    async def refresh_snapshot(self) -> PageSnapshot:
        self._snapshot = await snapshot_page(self.page)
        return self._snapshot

    async def screenshot_b64(self) -> str:
        png = await self.page.screenshot(full_page=False, type="png")
        return base64.b64encode(png).decode("ascii")

    async def execute(self, action: Action) -> str:
        """Run an action; return a short status string for the LLM."""
        if isinstance(action, ClickAction):
            return await self._click(action.target_id)
        if isinstance(action, TypeAction):
            return await self._type(action.target_id, action.text, action.submit)
        if isinstance(action, GotoAction):
            await self.page.goto(action.url, wait_until="domcontentloaded")
            return f"navigated to {action.url}"
        if isinstance(action, ScrollAction):
            delta = action.amount if action.direction == "down" else -action.amount
            await self.page.mouse.wheel(0, delta)
            return f"scrolled {action.direction} {action.amount}px"
        if isinstance(action, WaitAction):
            await asyncio.sleep(action.seconds)
            return f"waited {action.seconds}s"
        if isinstance(action, BackAction):
            await self.page.go_back(wait_until="domcontentloaded")
            return "went back"
        if isinstance(action, ScreenshotAction):
            return "screenshot requested"
        raise ValueError(f"Unknown action: {action!r}")

    async def _resolve(self, target_id: int):
        snap = self._snapshot
        if snap is None:
            raise RuntimeError("No DOM snapshot available; call refresh_snapshot() first.")
        if not 0 <= target_id < len(snap.elements):
            raise IndexError(
                f"target_id={target_id} out of range (0..{len(snap.elements) - 1})"
            )
        return self.page.locator(locator_selector()).nth(target_id)

    async def _click(self, target_id: int) -> str:
        loc = await self._resolve(target_id)
        await loc.scroll_into_view_if_needed(timeout=5000)
        await loc.click(timeout=10_000)
        return f"clicked element {target_id}"

    async def _type(self, target_id: int, text: str, submit: bool) -> str:
        loc = await self._resolve(target_id)
        await loc.scroll_into_view_if_needed(timeout=5000)
        await loc.click(timeout=10_000)
        # Clear existing content where possible, then type.
        try:
            await loc.fill("")
        except Exception:  # noqa: BLE001 — fill() doesn't apply to every element
            pass
        await loc.type(text, delay=15)
        if submit:
            await loc.press("Enter")
        return f"typed into element {target_id}" + (" and pressed Enter" if submit else "")


@asynccontextmanager
async def open_browser(config: Config) -> AsyncIterator[BrowserController]:
    """Launch a browser, yield a controller pre-attached to a blank page."""
    async with async_playwright() as pw:
        launcher = {
            "chromium": pw.chromium,
            "firefox": pw.firefox,
            "webkit": pw.webkit,
        }[config.browser]
        browser: Browser = await launcher.launch(headless=config.headless)
        try:
            context: BrowserContext = await browser.new_context(
                viewport={"width": config.viewport_width, "height": config.viewport_height},
            )
            page: Page = await context.new_page()
            yield BrowserController(page)
        finally:
            await browser.close()

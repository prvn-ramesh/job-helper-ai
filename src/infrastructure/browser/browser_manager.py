from __future__ import annotations

"""Browser Manager with Stealth and Anti-Detection.

Launches Playwright Chromium instances configured with realistic desktop
fingerprints, stealth overrides, human-like typing delays, and screenshot capture.
"""

import asyncio
import logging
import random
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from core.config import settings

log = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

STEALTH_JS = """
// Overwrite navigator.webdriver to avoid bot detection
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// Overwrite chrome runtime
window.chrome = {
    runtime: {},
    app: {},
};

// Overwrite languages and plugins
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});
"""


class BrowserManager:
    """Manages browser lifecycle, stealth configuration, and human interaction simulation."""

    def __init__(self, headless: bool | None = None) -> None:
        self.headless = headless if headless is not None else settings.headless
        self._playwright = None
        self._browser: Browser | None = None

    async def get_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                ],
            )
        return self._browser

    async def create_context(self) -> BrowserContext:
        """Create a browser context with realistic fingerprinting."""
        browser = await self.get_browser()
        context = await browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )
        await context.add_init_script(STEALTH_JS)
        return context

    async def new_page(self) -> Page:
        """Create and return a configured stealth page."""
        context = await self.create_context()
        page = await context.new_page()
        page.set_default_timeout(25000)
        return page

    async def human_type(self, page: Page, selector: str, text: str, delay_range: tuple[int, int] = (25, 65)) -> None:
        """Type text into an input field with human-like keystroke intervals."""
        await page.click(selector)
        # Clear field first
        await page.fill(selector, "")
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(delay_range[0], delay_range[1]) / 1000.0)

    async def capture_screenshot(self, page: Page, destination_path: str | Path) -> str:
        """Capture a full-page verification screenshot."""
        p = Path(destination_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(p), full_page=True)
        log.info("Captured form verification screenshot: %s", p)
        return str(p)

    async def close(self) -> None:
        """Clean up browser and playwright instances."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

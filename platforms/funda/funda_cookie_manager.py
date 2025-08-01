import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright

from base.base_cookie_manager import AbstractCookieManager
from tools import utils

logger = logging.getLogger(__name__)


class FundaCookieManager(AbstractCookieManager):
    """
    Manages Funda cookies, including fetching, caching, and refreshing.
    """

    def __init__(
        self,
        cookie_file_path: str = "data/funda_cookie.json",
        cookie_lifetime: int = 7200,
    ):
        self.cookie_file_path = Path(cookie_file_path)
        self.cookie_lifetime = cookie_lifetime  # Default lifetime is 1 hour
        self._cookie_data = self._load_cookie()

    async def get_cookie(self, force_refresh: bool = False) -> str:
        if not force_refresh and self._is_cookie_valid():
            logger.info("Using cached valid cookie.")
            return self._cookie_data["cookie_string"]

        logger.info("Fetching a new cookie.")
        new_cookie_string = await self._fetch_new_cookie()
        self._cookie_data = {
            "cookie_string": new_cookie_string,
            "timestamp": time.time(),
        }
        self._save_cookie(self._cookie_data)
        return new_cookie_string

    def _load_cookie(self) -> Optional[dict]:
        if not self.cookie_file_path.exists():
            return None
        try:
            with open(self.cookie_file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load cookie file: {e}")
            return None

    def _save_cookie(self, cookie_data: dict):
        self.cookie_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cookie_file_path, "w") as f:
                json.dump(cookie_data, f)
        except IOError as e:
            logger.error(f"Failed to save cookie file: {e}")

    async def _fetch_new_cookie(self) -> str:
        async with async_playwright() as playwright:
            chromium = playwright.chromium
            browser = await chromium.launch(headless=False)
            context = await browser.new_context(user_agent=utils.get_user_agent())
            await context.add_init_script(path="libs/stealth.min.js")
            page = await context.new_page()

            try:
                await page.goto("https://www.funda.nl/en", timeout=60000)

                try:
                    agree_button = await page.wait_for_selector(
                        "//button[@id='didomi-notice-agree-button']",
                        state="visible",
                        timeout=5000,
                    )
                    await agree_button.click()
                    logger.info("Clicked the cookie consent button.")
                except Exception:
                    logger.info("Cookie consent button not found, proceeding.")

                cookies = await context.cookies()
                cookie_str, _ = utils.convert_cookies(cookies)
                return cookie_str
            finally:
                await browser.close()

    def _is_cookie_valid(self) -> bool:
        if not self._cookie_data:
            return False

        current_time = time.time()
        cookie_timestamp = self._cookie_data.get("timestamp", 0)

        return (current_time - cookie_timestamp) < self.cookie_lifetime


# Create a single, shared instance of the cookie manager
funda_cookie_manager = FundaCookieManager()

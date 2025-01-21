from abc import ABC, abstractmethod
from typing import Dict, Optional

from playwright.async_api import BrowserContext, BrowserType


class AbstractCrawler(ABC):
    @abstractmethod
    async def start(self):
        """
        start crawler
        """
        pass

    @abstractmethod
    async def crawl_info(self):
        """
        crawl info
        """
        pass

    @abstractmethod
    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        launch browser
        :param chromium: chromium browser
        :param playwright_proxy: playwright proxy
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        pass


class AbstractStore(ABC):
    @abstractmethod
    async def store_decription(self, description_item: Dict):
        pass

    @abstractmethod
    async def store_image(self, image_item: Dict):
        pass

    @abstractmethod
    async def store_details(self, details: Dict):
        pass


class AbsstractCaptchaSolver(ABC):
    @abstractmethod
    async def solve(self, image_path, target):
        pass

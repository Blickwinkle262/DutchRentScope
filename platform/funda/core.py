import asyncio
import os
import random
import hashlib
import time
import random
import uuid
import json
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright

import config
from base.base import AbstractCrawler
from tools import utils

from .client import FundaClient, FundaPlaywrightClient
from .param import OffereingType
from .help import FundaExtractor


class FundaCrawler(AbstractCrawler):
    context_page: Page
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.funda.nl"
        self.user_agent = utils.get_user_agent()
        self._page_extractor = FundaExtractor()

    async def start(self) -> None:
        if config.funda_crawl_type == "basic":
            self.client = await self.create_funda_client(httpx_proxy=None)
            search_result = await self.client.get_single_page_house_info(
                selected_area=["leiden"], offering_type=OffereingType.rent
            )
            print(search_result)
            parsed_result = await self.client.parse_single_page_house_info(
                search_result
            )
            if parsed_result.properties:
                prop = parsed_result.properties[0]
                print(f"\nFirst property details:")
                print(f"ID: {prop.id}")
                print(f"Type: {prop.object_type}")
                print(
                    f"Price: {prop.price.rent_price[0] if prop.price.rent_price else 0} {prop.price.rent_price_condition}"
                )
                print(
                    f"Location: {prop.address.street_name} {prop.address.house_number}"
                )
                print(
                    f"Rooms: {prop.number_of_rooms} (Bedrooms: {prop.number_of_bedrooms})"
                )
                print(f"Area: {prop.floor_area[0] if prop.floor_area else 0} m²")
                print(f"Energy Label: {prop.energy_label}")

        elif config.funda_crawl_type == "detail":
            async with async_playwright() as playwright:
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium, None, self.user_agent, headless=False
                )
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

                self.context_page = await self.browser_context.new_page()
                # self.context_page.on("request", self.handle_request)
                await self.context_page.goto(self.index_url)

                agree_bottom = await self.context_page.wait_for_selector(
                    "//button[@id='didomi-notice-agree-button']", state="visible"
                )
                await agree_bottom.click(click_count=1)

                print("loaded")

                await self.context_page.wait_for_timeout(5000)

                self.playwright_client = await self.create_funda_playwright_client(
                    httpx_proxy=None
                )

                # search_result = await self.playwright_client.get_house_info(
                #     selected_area=["leiden"], offering_type="buy"
                # )

                # print(search_result)

                # if config.CRAWL_TYPE == "Basic":
                #     await self.crawl_info()
                # elif config.CRAWL_TYPE == "Details":
                #     await self.crawl_info(callback=self._crawl_detail_info)
                # else:
                #     pass

                print("finished")

        else:
            raise NotImplemented("")

    async def get_basic_info(self):
        print("begin searching housing")
        funda_limit = 20

    # async def handle_request(self, request):
    #     if request.url.endswith("/zoeken/huur"):
    #         headers = request.headers
    #         # 保存请求头到文件
    #         with open("playwright_headers.json", "w") as f:
    #             json.dump(headers, f, indent=2)
    #         print("已保存请求头到 playwright_headers.json")

    async def captcha_check(self):
        if self.context_page is None:
            return False
        else:
            pass

    async def captcha_solver(self):
        pass

    async def crawl_info(self, callback=None):
        pass

    async def _crawl_detail_info(self):
        pass

    def generate_oidc_state(self):
        # 方法1：使用 UUID + 时间戳
        base = f"{uuid.uuid4()}{int(time.time())}"
        return hashlib.sha256(base.encode()).hexdigest()[:32]

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = config.HEADLESS,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        print("[FundaCrawler.launch_browser] Begin create browser context ...")

        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
        browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, user_agent=user_agent
        )
        return browser_context

    async def print_cookies(self, context: BrowserContext):
        """Print all cookies"""
        cookies = await context.cookies()
        print("[FundaCrawler.print_cookies] Current cookies:")
        for cookie in cookies:
            print(f"Name: {cookie['name']}")
            print(f"Value: {cookie['value']}")
            print(f"Domain: {cookie.get('domain', 'N/A')}")
            print(f"Path: {cookie.get('path', '/')}")
            print("---")

    async def create_static_funda_client(
        self, httpx_proxy: Optional[str]
    ) -> FundaClient:
        print("creating static funda api client")

    async def create_funda_client(self, httpx_proxy: Optional[str]) -> FundaClient:
        funda_client = FundaClient(headers=config.funda_headers)
        return funda_client

    async def create_funda_playwright_client(
        self, httpx_proxy: Optional[str]
    ) -> FundaPlaywrightClient:
        print(" creating funda api client")

        cookies = await self.browser_context.cookies()
        cookie_str, cookie_dict = utils.convert_cookies(cookies)
        print(cookie_str)
        funda_client = FundaPlaywrightClient(
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Host": "www.funda.nl",
                "Content-Type": "text/html;charset=utf-8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return funda_client


if __name__ == "__main__":
    asyncio.run(FundaCrawler().start())

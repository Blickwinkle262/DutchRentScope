import asyncio
import aiohttp
import math
import os
import logging

from asyncio import Task
from collections import namedtuple
from typing import Dict, List, Optional, NamedTuple
from pathlib import Path


from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright

import config
from base.base import AbstractCrawler
from tools import utils

from .client import FundaClient, FundaPlaywrightClient
from model.m_search import OfferingType, PriceRange
from .help import FundaDetailExtractor
from store import StoreFactory

logger = logging.getLogger("funda")


class HouseDetailReference(NamedTuple):
    house_id: str
    detail_uri: str


class FundaCrawler(AbstractCrawler):
    context_page: Page
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.funda.nl/en"
        self.user_agent = utils.get_user_agent()
        self._page_extractor = FundaDetailExtractor()
        if config.SAVE_DATA_OPTION:
            self.store = StoreFactory.create_store(config.SAVE_DATA_OPTION)

    async def start(self) -> None:

        await self._initialize_base_client()

        if config.FUNDA_CRAWL_TYPE == "listing":
            listing_results = await self._get_listing_info()
            detailed_results = None

        elif config.FUNDA_CRAWL_TYPE == "detail":
            listing_results = await self._get_listing_info()

            detail_references = [
                HouseDetailReference(prop.id, prop.detail_page_relative_url)
                for prop in listing_results
            ]

            detailed_results = await self._get_detailed_info(detail_references)

        else:
            raise ValueError(f"Unsupported crawl type: {config.FUNDA_CRAWL_TYPE}")

        if self.store:
            logger.info("Starting data storage process")

            # Store listing results
            for result in listing_results:
                try:
                    await self.store.store_listing(result.to_flat_dict())
                except Exception as e:
                    logger.error(
                        "Failed to store listing [ID: %s]: %s",
                        result.id,
                        str(e),
                        exc_info=True,
                    )
            logger.info("Completed storing %d listings", len(listing_results))

            # Store detail results if available
            if detailed_results is not None:
                for house_id, detail in detailed_results:
                    try:
                        await self.store.store_details(detail.to_dict_items())
                    except Exception as e:
                        logger.error(
                            "Failed to store details [ID: %s]: %s",
                            house_id,
                            str(e),
                            exc_info=True,
                        )
                logger.info(
                    "Completed storing %d property details", len(detailed_results)
                )
        else:
            logger.warning("No storage configured - skipping data storage")

    async def _initialize_base_client(self):
        """Initialize the basic HTTP client for listing operations"""
        self.client = await self.create_funda_client(httpx_proxy=None)

    async def _initialize_playwright_client(self):
        self.playwright_client = await self.create_funda_playwright_client(
            httpx_proxy=None
        )

    async def _get_listing_info(self):
        search_areas = config.SEARCH_AREAS
        offering_type = (
            OfferingType.rent if config.OFFERING_TYPE == "rent" else OfferingType.buy
        )
        start_page = config.START_PAGE
        end_page = config.END_PAGE
        min_price = config.PRICE_MIN
        max_price = config.PRICE_MAX
        price_range = PriceRange(min_price, max_price)

        if config.END_PAGE:
            end_page = config.END_PAGE
        return await self.get_house_info(
            search_areas=search_areas,
            offering_type=offering_type,
            start_page=start_page,
            end_page=end_page,
            price_range=price_range,
        )

    async def _get_detailed_info(self, detail_list: List[HouseDetailReference]):
        result = []
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

            logger.info("loaded")

            # await self.context_page.wait_for_timeout(500)
            await self._initialize_playwright_client()
            semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
            task_list = [
                (
                    detail.house_id,
                    self.playwright_client.get_house_detail_info(
                        detail.detail_uri, semaphore
                    ),
                )
                for detail in detail_list
            ]

            house_details = []
            for house_id, task in task_list:
                detail = await task
                if detail is not None:
                    house_details.append((house_id, detail))

            for house_id, house in house_details:
                if house is not None:
                    try:
                        house_info = await self._page_extractor.extract_details(house)
                        logger.info(
                            "Successfully extracted house details [ID: %s] | Price: %s, Area: %s, Label: %s, Status: %s, Type: %s, Description %s",
                            house_id,
                            house_info.price or "N/A",
                            house_info.living_area or "N/A",
                            house_info.energy_label or "N/A",
                            house_info.status or "N/A",
                            house_info.house_type or "N/A",
                            house_info.description[:50] or "N/A",
                        )

                        result.append((house_id, house_info))

                    except (TypeError, AttributeError) as e:
                        logger.error(
                            "Failed to extract house details [ID: %s]",
                            house_id,
                            exc_info=True,
                            extra={
                                "house_id": house_id,
                                "error_type": type(e).__name__,
                            },
                        )
                else:
                    logger.error(
                        "parse failed on %s with html %s",
                        house_id,
                        house,
                        exc_info=True,
                    )
            return result

    async def _handle_download_imgs(self, house_lists):
        for prop in house_lists:
            house_name = f"{prop.address.municipality}{prop.address.street_name} {prop.address.postal_code}{prop.address.house_number}"
            thumbnail_ids = prop.thumbnail_id
            download_result = await self.download_imgs(thumbnail_ids, house_name)
            for house_name, success in download_result.items():
                logger.debug("House %s: suceess %s", house_name, success)

    async def log_cookies(self, context: BrowserContext):
        """Log all browser context cookies"""
        cookies = await context.cookies()
        for cookie in cookies:
            logger.debug(
                "Cookie: name=%s, value=%s, domain=%s, path=%s",
                cookie["name"],
                cookie["value"],
                cookie.get("domain", "N/A"),
                cookie.get("path", "/"),
            )

    async def create_funda_client(self, httpx_proxy: Optional[str]) -> FundaClient:
        funda_client = FundaClient(headers=utils.funda_headers)
        return funda_client

    async def create_funda_playwright_client(
        self, httpx_proxy: Optional[str]
    ) -> FundaPlaywrightClient:
        logger.info(" creating funda api client")
        required_cookies = {
            ".ASPXANONYMOUS",
            "sr",
            "SNLB",
            "didomi_consent",
            "didomi_token",
            "bm_sv",
        }

        cookie_str, cookie_dict = utils.convert_cookies(
            await self.browser_context.cookies(), required_cookies
        )
        # cookie_dict = utils.convert_str_cookie_to_dict(cookie_str)
        logger.debug(cookie_str)
        funda_client = FundaPlaywrightClient(
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-GPC": "1",
                "Host": "www.funda.nl",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return funda_client

    async def fetch_page(self, search_areas, offering_type, page, price_range=None):
        current_page = await self.client.get_single_page_house_info(
            search_areas, offering_type, price_range=price_range, page=page
        )
        parsed_result = await self.client.parse_single_page_house_info(current_page)
        if parsed_result.properties:
            return parsed_result.properties
        return []

    async def get_house_info(
        self,
        search_areas: List[str],
        offering_type: OfferingType,
        start_page: int = 1,
        end_page: int | None = None,
        price_range: PriceRange | None = None,
    ) -> List[property]:
        total_properties = []
        logger.info(
            "Starting house search - Areas: %s, Type: %s, Price Range: %s",
            search_areas,
            offering_type,
            (
                f"€{price_range.from_price}-{price_range.to_price}"
                if price_range
                else "No limit"
            ),
        )
        first_page = await self.client.get_single_page_house_info(
            search_areas, offering_type, page=start_page, price_range=price_range
        )

        first_page_houses = await self.client.parse_single_page_house_info(first_page)
        logger.info(
            logger.info(
                "Processing results from page %d (%d properties)",
                start_page,
                len(first_page_houses.properties),
            )
        )
        for property in first_page_houses.properties:
            logger.info(
                "Property Details [ID: %s] | Price: €%.2f/%s, Rooms: %d, Area: %.1fm², Label: %s | %s, %s %s",
                property.id,
                property.price.rent_price[0],
                property.price.rent_price_condition,
                property.number_of_rooms,
                property.floor_area[0],
                property.energy_label,
                property.address.street_name,
                property.address.house_number,
                property.address.city,
            )

        page_nums = math.ceil(first_page_houses.total_value / 15)
        total_properties.extend(first_page_houses.properties)

        if end_page is not None:
            end_page = min(end_page, page_nums + 1)
            if end_page <= start_page:
                return total_properties
        else:
            end_page = page_nums + 1

        tasks = [
            self.fetch_page(search_areas, offering_type, page, price_range)
            for page in range(start_page + 1, end_page)
        ]

        if tasks:
            results = await asyncio.gather(*tasks)
            for page_num, page_properties in enumerate(results, start=start_page + 1):
                logger.info(
                    "Processing results from page %d (%d properties)",
                    page_num,
                    len(page_properties),
                )
                for property in page_properties:
                    logger.info(
                        "Property Details [ID: %s] | Price: €%.2f/%s, Rooms: %s, Area: %s, Label: %s | %s, %s %s",
                        property.id,
                        (
                            property.price.rent_price[0]
                            if property.price.rent_price
                            else 0.0
                        ),
                        property.price.rent_price_condition or "N/A",
                        property.number_of_rooms or "N/A",
                        (
                            f"{property.floor_area[0]:.1f}m²"
                            if property.floor_area
                            else "N/A"
                        ),
                        property.energy_label or "N/A",
                        property.address.street_name or "N/A",
                        property.address.house_number or "N/A",
                        property.address.city or "N/A",
                    )
                total_properties.extend(page_properties)

        return total_properties

    async def download_imgs(
        self,
        thumbnail_ids: list[str],
        house_name: str,
        base_path: str | Path = "data/house_images",
        img_size: str = "medium",
    ) -> dict[str, bool]:

        base_path = Path(base_path)
        house_dir = base_path / house_name
        os.makedirs(house_dir, exist_ok=True)

        results = {}

        async with aiohttp.ClientSession() as session:
            download_tasks = []

            # Create all download tasks
            for thumb_id in thumbnail_ids:
                url = utils.generate_image_url(thumb_id, img_size)
                save_path = house_dir / f"{thumb_id}.jpg"
                task = utils.download_single_image(url, save_path, session)
                download_tasks.append((thumb_id, task))

            for thumb_id, task in download_tasks:
                success = await task
                results[thumb_id] = success

        return results

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = config.HEADLESS,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        logger.info("[FundaCrawler.launch_browser] Begin create browser context ...")

        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
        browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}, user_agent=user_agent
        )
        return browser_context

    async def close(self):
        await self.browser_context.close()

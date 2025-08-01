import asyncio
import aiohttp
import math
import os
import logging
import random

from asyncio import Task
from collections import namedtuple
from typing import Dict, List, Optional, NamedTuple
from pathlib import Path


from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright

import config
from base.base import AbstractCrawler
from tools import utils

from .client import FundaClient, FundaPlaywrightClient
from .exception import PaginationLimitError, EmptyResponseError, IPBlockError
from .funda_cookie_manager import funda_cookie_manager
from model.m_search import OfferingType, PriceRange
from .help import FundaBuyExtractor, FundaRentExtractor
from store import StoreFactory

logger = logging.getLogger("funda")


class HouseDetailReference(NamedTuple):
    house_id: str
    detail_uri: str


class FundaCrawler(AbstractCrawler):
    def __init__(self) -> None:
        self.user_agent = utils.get_user_agent()
        self.cookie_manager = funda_cookie_manager
        self.index_url = "https://www.funda.nl/en"
        self._page_extractor = None
        if config.SAVE_DATA_OPTION:
            self.store = StoreFactory.create_store(
                config.SAVE_DATA_OPTION,
                offering_type=config.OFFERING_TYPE,
                search_areas=config.SEARCH_AREAS,
            )

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
                logger.info("Storing %d detailed results...", len(detailed_results))
                for house_id, detail in detailed_results:
                    try:
                        # Assuming the store_details method can handle the data format
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
        all_results = []
        batch_size = config.BATCH_SIZE

        await self._initialize_playwright_client()

        offering_type = config.OFFERING_TYPE
        if offering_type == "buy":
            self._page_extractor = FundaBuyExtractor()
        elif offering_type == "rent":
            self._page_extractor = FundaRentExtractor()
        else:
            raise ValueError(
                f"Unsupported offering_type for detail extraction: {offering_type}"
            )

        for i in range(0, len(detail_list), batch_size):
            batch = detail_list[i : i + batch_size]
            logger.info(
                f"Processing batch {i//batch_size + 1} of {math.ceil(len(detail_list)/batch_size)}..."
            )

            semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
            fetch_tasks = [
                self._fetch_and_parse_detail(detail, semaphore) for detail in batch
            ]

            results = await asyncio.gather(*fetch_tasks)
            for result in results:
                if result:
                    all_results.append(result)

        return all_results

    async def _fetch_and_parse_detail(
        self, detail: HouseDetailReference, semaphore: asyncio.Semaphore
    ):
        """
        Fetches and parses a single house detail page.
        """
        html_content = None
        async with semaphore:
            try:
                html_content = await self.playwright_client.get_house_detail_info(
                    detail.detail_uri
                )
                if not html_content:
                    logger.warning(
                        "Received empty HTML content for house ID: %s", detail.house_id
                    )
                    return None

                if "Je bent bijna op de pagina die je zoekt" in html_content:
                    raise IPBlockError("Captcha page detected.")

                house_info = await self._page_extractor.extract_details(
                    id=detail.house_id, page_content=html_content
                )

                # Define essential numeric fields that should not be zero
                essential_fields = ["price"]

                # Check for partial parsing failure
                is_partial_failure = any(
                    getattr(house_info, field, 0) == 0 for field in essential_fields
                )

                if is_partial_failure:
                    raise ValueError(
                        "Partial parsing failure: one or more essential fields are missing."
                    )

                logger.info(
                    "Successfully extracted house details [ID: %s] | Price: %s, Area: %s, Label: %s, Status: %s, Type: %s",
                    detail.house_id,
                    house_info.price or "N/A",
                    house_info.living_area or "N/A",
                    house_info.energy_label or "N/A",
                    house_info.status or "N/A",
                    house_info.house_type or "N/A",
                )
                return (detail.house_id, house_info)

            except IPBlockError:
                logger.warning(
                    "IP blocked for house ID %s, trying to refresh cookie...",
                    detail.house_id,
                )
                await self.cookie_manager.get_cookie(force_refresh=True)
                # We don't retry here, but the next run with a fresh cookie should succeed.

            except Exception as e:
                logger.error(
                    "Failed to process detail for house [ID: %s]: %s",
                    detail.house_id,
                    str(e),
                    exc_info=True,
                )
                if html_content:
                    logger.error(
                        "--- HTML content for failed extraction [ID: %s] ---\n%s",
                        detail.house_id,
                        html_content,
                    )
        return None

    async def _handle_download_imgs(self, house_lists):
        for prop in house_lists:
            house_name = f"{prop.address.municipality}{prop.address.street_name} {prop.address.postal_code}{prop.address.house_number}"
            thumbnail_ids = prop.thumbnail_id
            download_result = await self.download_imgs(
                house_id=prop.id, thumbnail_ids=thumbnail_ids, house_name=house_name
            )
            for thumb_id, success in download_result.items():
                logger.debug(
                    "Image download for house %s, thumb_id %s: %s",
                    house_name,
                    thumb_id,
                    success,
                )

    async def create_funda_client(self, httpx_proxy: Optional[str]) -> FundaClient:
        funda_client = FundaClient(headers=utils.funda_headers)
        return funda_client

    async def create_funda_playwright_client(
        self, httpx_proxy: Optional[str]
    ) -> FundaPlaywrightClient:
        logger.info("Creating Funda API client for detail fetching.")

        cookie_str = await self.cookie_manager.get_cookie()
        cookie_dict = {
            cookie.split("=")[0]: cookie.split("=")[1]
            for cookie in cookie_str.split("; ")
        }

        funda_client = FundaPlaywrightClient(
            headers={
                "authority": "www.funda.nl",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
                "priority": "u=0, i",
                "referer": "https://www.funda.nl/zoeken/koop?selected_area=[%22leiden%22]",
                "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "sec-gpc": "1",
                "upgrade-insecure-requests": "1",
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
            },
            playwright_page=None,  # No longer needed
            cookie_dict=cookie_dict,
        )
        return funda_client

    async def fetch_page(self, search_areas, offering_type, page, price_range=None):
        """
        Fetch and parse a single page of property listings with error handling.

        Args:
            search_areas: List of search areas
            offering_type: Type of offering (rent/buy)
            page: Page number to fetch
            price_range: Price range filter

        Returns:
            List of properties or empty list on error
        """
        try:
            current_page = await self.client.get_single_page_house_info(
                search_areas, offering_type, price_range=price_range, page=page
            )
            parsed_result = await self.client.parse_single_page_house_info(
                response_data=current_page, offering_type=offering_type
            )
            if parsed_result.properties:
                return parsed_result.properties
            return []
        except PaginationLimitError as e:
            logger.error("Pagination limit exceeded on page %d: %s", page, str(e))
            logger.warning(
                "Stopping pagination at page %d due to search engine limits. "
                "Consider using more specific search criteria to reduce total results.",
                page,
            )
            return []  # Return empty list to stop pagination gracefully
        except EmptyResponseError as e:
            logger.error("Empty response received for page %d: %s", page, str(e))
            return []
        except Exception as e:
            logger.error(
                "Unexpected error fetching page %d: %s", page, str(e), exc_info=True
            )
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
        try:
            first_page = await self.client.get_single_page_house_info(
                search_areas, offering_type, page=start_page, price_range=price_range
            )

            first_page_houses = await self.client.parse_single_page_house_info(
                response_data=first_page, offering_type=offering_type
            )
        except PaginationLimitError as e:
            logger.error(
                "Pagination limit exceeded on first page (page %d): %s",
                start_page,
                str(e),
            )
            logger.error(
                "Cannot proceed with search - pagination limit reached immediately. "
                "Try using more specific search criteria to reduce total results."
            )
            return []  # Return empty list as we can't even get the first page
        except EmptyResponseError as e:
            logger.error(
                "Empty response received for first page (page %d): %s",
                start_page,
                str(e),
            )
            return []
        except Exception as e:
            logger.error(
                "Unexpected error fetching first page (page %d): %s",
                start_page,
                str(e),
                exc_info=True,
            )
            return []

        logger.info(
            "Processing results from page %d (%d properties)",
            start_page,
            len(first_page_houses.properties),
        )

        for property in first_page_houses.properties:
            if offering_type == OfferingType.rent:
                # situation rent
                price_display = f"€{property.price.rent_price[0]:.2f}/{property.price.rent_price_condition}"
            else:
                # situation buy
                price_display = f"€{property.price.selling_price[0]:,.2f}"

            # 构建房号显示（包含后缀）
            house_number_display = property.address.house_number
            if property.address.house_number_suffix:
                house_number_display += f" {property.address.house_number_suffix}"

            living_area_display = (
                f"{property.floor_area[0]:.1f}m²" if property.floor_area else "N/A"
            )
            logger.info(
                "Property Details [ID: %s] [%s] | Price: %s, Rooms: %d, Area: %s, Label: %s | %s, %s %s",
                property.id,
                property.offering_type[0].upper(),  # 显示 RENT 或 BUY
                price_display,
                property.number_of_rooms,
                living_area_display,
                property.energy_label,
                property.address.street_name,
                house_number_display,
                property.address.city,
            )

        page_nums = math.ceil(first_page_houses.total_value / 15)
        logger.info(
            "Total page num %d with total houses %d",
            page_nums,
            first_page_houses.total_value,
        )
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
                for property in first_page_houses.properties:
                    if offering_type == OfferingType.rent:
                        # situation rent
                        price_display = f"€{property.price.rent_price[0]:.2f}/{property.price.rent_price_condition}"
                    else:
                        # situation buy
                        price_display = f"€{property.price.selling_price[0]:,.2f}"

                    # 构建房号显示（包含后缀）
                    house_number_display = property.address.house_number
                    if property.address.house_number_suffix:
                        house_number_display += (
                            f" {property.address.house_number_suffix}"
                        )

                    living_area_display = (
                        f"{property.floor_area[0]:.1f}m²"
                        if property.floor_area
                        else "N/A"
                    )
                    logger.info(
                        "Property Details [ID: %s] [%s] | Price: %s, Rooms: %d, Area: %s, Label: %s | %s, %s %s",
                        property.id,
                        property.offering_type[0].upper(),  # 显示 RENT 或 BUY
                        price_display,
                        property.number_of_rooms,
                        living_area_display,
                        property.energy_label,
                        property.address.street_name,
                        house_number_display,
                        property.address.city,
                    )
                total_properties.extend(page_properties)

        return total_properties

    async def download_imgs(
        self,
        house_id: int,
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
                download_tasks.append((thumb_id, url, save_path, task))

            for thumb_id, url, save_path, task in download_tasks:
                success = await task
                results[thumb_id] = success
                if success and config.SAVE_DATA_OPTION == "postgres":
                    image_data = {
                        "house_id": house_id,
                        "image_url": url,
                        "local_path": str(save_path),
                    }
                    await self.store.store_image(image_data)

        return results

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        This method is required by the AbstractCrawler, but is not used by FundaCrawler.
        The browser is launched by the CookieManager.
        """
        pass

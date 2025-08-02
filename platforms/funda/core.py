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
from model.m_search import (
    OfferingType,
    PriceRange,
    SearchParams,
    Page,
    Price,
    Availability,
    ConstructionPeriod,
)
from model.m_response import Property
from model.m_house_detail import HouseDetail
from .help import FundaBuyExtractor, FundaRentExtractor
from store import StoreFactory

logger = logging.getLogger("funda")


class HouseDetailReference(NamedTuple):
    house_id: str
    detail_uri: str
    city: str
    listing_data: Optional[Property] = None  # Carry the full listing object


class FundaCrawler(AbstractCrawler):
    def _build_search_params(self, page_num: int) -> SearchParams:
        """Builds the SearchParams object from config."""
        price = None
        if config.PRICE_MIN is not None or config.PRICE_MAX is not None:
            price = Price(
                rent_price=(
                    PriceRange(config.PRICE_MIN, config.PRICE_MAX)
                    if config.OFFERING_TYPE == "rent"
                    else None
                ),
                selling_price=(
                    PriceRange(config.PRICE_MIN, config.PRICE_MAX)
                    if config.OFFERING_TYPE == "buy"
                    else None
                ),
            )

        # Convert string values from config to Enum members if they exist
        availability_enums = (
            [Availability(item) for item in config.AVAILABILITY]
            if config.AVAILABILITY
            else None
        )
        construction_period_enums = (
            [ConstructionPeriod(item) for item in config.CONSTRUCTION_PERIOD]
            if config.CONSTRUCTION_PERIOD
            else None
        )

        params = SearchParams(
            selected_area=config.SEARCH_AREAS,
            offering_type=OfferingType(config.OFFERING_TYPE),
            page=Page(from_=page_num),
            price=price,
            availability=availability_enums,
            construction_period=construction_period_enums,
            free_text_search="",  # Required field, but not used in current cmd logic
        )
        return params

    def __init__(self) -> None:
        self.user_agent = utils.get_user_agent()
        self.cookie_manager = funda_cookie_manager
        self.index_url = "https://www.funda.nl/en"
        self._page_extractor = None
        self.playwright_client = None
        self.cookie_update_attempts = 0
        self.crawler_id = random.randint(1000, 9999)
        logger.info(f"[{self.crawler_id}] FundaCrawler instance created.")
        self.processed_listing_ids = set()  # Duplicate ID detector
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)

        # Summary statistics
        self.snapshots_stored = 0
        self.error_html_saved = 0
        self.ip_block_count = 0
        self.parsing_failures = 0
        self.tombstones_created = 0

        if config.SAVE_DATA_OPTION:
            self.store = StoreFactory.create_store(
                config.SAVE_DATA_OPTION,
                offering_type=config.OFFERING_TYPE,
                search_areas=config.SEARCH_AREAS,
            )

    def _print_summary_report(self):
        """Prints a summary of the crawl results."""
        report = (
            "--- Crawl Summary Report ---\n"
            f"Snapshots Stored:     {self.snapshots_stored}\n"
            f"Tombstones Created:   {self.tombstones_created}\n"
            f"IP Blocked Count:     {self.ip_block_count}\n"
            f"Parsing Failures:     {self.parsing_failures}\n"
            f"Error HTMLs Saved:    {self.error_html_saved}\n"
            "--------------------------"
        )
        logger.info(report)

    async def start(self) -> None:
        logger.info(f"[{self.crawler_id}] Crawler starting...")
        await self._initialize_base_client()

        try:
            if config.FUNDA_CRAWL_TYPE == "listing":
                # This mode remains a bulk operation as it doesn't fetch details.
                listing_results = await self._get_listing_info()
                if self.store:
                    logger.info(f"Storing {len(listing_results)} listings...")
                    for result in listing_results:
                        try:
                            await self.store.store_listing(result.to_flat_dict())
                            self.snapshots_stored += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to store listing [ID: {result.id}]: {e}",
                                exc_info=True,
                            )
                    logger.info("Completed storing listings.")

            elif config.FUNDA_CRAWL_TYPE == "detail":
                # Pipeline mode for fetching and storing details
                await self._run_detail_pipeline()

            elif config.FUNDA_CRAWL_TYPE == "update":
                # Update mode for re-crawling available listings
                await self._run_update_pipeline()

            else:
                raise ValueError(f"Unsupported crawl type: {config.FUNDA_CRAWL_TYPE}")
        finally:
            self._print_summary_report()
        logger.info(f"[{self.crawler_id}] Crawler finished.")

    async def _run_detail_pipeline(self):
        """
        Runs the full listing -> detail -> store pipeline.
        """
        listing_generator = self.get_house_info_generator()

        page_count = 0
        async for page_listings in listing_generator:
            page_count += 1
            logger.debug(
                f"Processing page {page_count} with {len(page_listings)} listings."
            )
            if not page_listings:
                continue

            detail_references = []
            for prop in page_listings:
                if prop.id in self.processed_listing_ids:
                    logger.warning(
                        f"[{self.crawler_id}] DUPLICATE ID DETECTED in listing feed: House ID {prop.id} was already processed."
                    )
                    continue  # Skip this duplicate property entirely

                self.processed_listing_ids.add(prop.id)

                try:
                    # Carry the full listing object (prop) for later merging
                    detail_references.append(
                        HouseDetailReference(
                            house_id=prop.id,
                            detail_uri=prop.detail_page_relative_url,
                            city=prop.address.city,
                            listing_data=prop,
                        )
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to store listing [ID: {prop.id}], skipping detail fetch. Error: {e}",
                        exc_info=True,
                    )

            # Now fetch and store details for the successfully stored listings
            if detail_references:
                await self._get_and_store_detailed_info(detail_references)

            # After processing details, handle image downloads for the current page
            if config.DOWNLOAD_IMAGES and page_listings:
                logger.info(
                    f"Handling image downloads for {len(page_listings)} listings on page {page_count}."
                )
                await self._handle_download_imgs(page_listings)

    async def _run_update_pipeline(self):
        """
        Runs the update pipeline for available listings.
        """
        if not self.store:
            logger.error("Update mode requires a store to be configured.")
            return

        available_listings = await self.store.get_available_listings()
        logger.info(
            f"Found {len(available_listings)} available listings to update from the active queue."
        )

        if not available_listings:
            return

        # For update mode, we don't have listing data, so we pass None.
        # The detail page will be the primary source of data.
        detail_references = [
            HouseDetailReference(
                house_id=item["listing_id"],
                detail_uri=f"/en/{config.OFFERING_TYPE}/placeholder-city/placeholder-type-{item['listing_id']}",
                city="Unknown",
                listing_data=None,
            )
            for item in available_listings
        ]

        await self._get_and_store_detailed_info(detail_references)

    async def _initialize_base_client(self):
        """Initialize the basic HTTP client for listing operations"""
        self.client = await self.create_funda_client(httpx_proxy=None)

    async def _initialize_playwright_client(self):
        self.playwright_client = await self.create_funda_playwright_client(
            httpx_proxy=None
        )

    async def _get_listing_info(self):
        """
        Gets all listings as a single list. Used for 'listing' crawl type.
        This method consumes the generator to produce a flat list.
        """
        all_properties = []
        listing_generator = self.get_house_info_generator()
        async for page_listings in listing_generator:
            if page_listings:
                all_properties.extend(page_listings)
        return all_properties

    async def _get_and_store_detailed_info(
        self, detail_list: List[HouseDetailReference]
    ):
        logger.info(f"Fetching details for {len(detail_list)} listings.")
        batch_size = config.BATCH_SIZE

        if not self.playwright_client:
            await self._initialize_playwright_client()

        if not self._page_extractor:
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
            # Add random delay between batches, but not before the first one.
            if i > 0 and config.RANDOM_DELAY_MAX > 0:
                delay = random.uniform(config.RANDOM_DELAY_MIN, config.RANDOM_DELAY_MAX)
                logger.info(
                    f"Waiting for {delay:.2f} seconds before processing next batch..."
                )
                await asyncio.sleep(delay)

            batch = detail_list[i : i + batch_size]
            logger.debug(
                f"Processing detail batch {i//batch_size + 1}/{math.ceil(len(detail_list)/batch_size)}..."
            )

            fetch_tasks = [
                self._fetch_parse_and_store_detail(detail) for detail in batch
            ]
            await asyncio.gather(*fetch_tasks)

    async def _fetch_parse_and_store_detail(self, detail_ref: HouseDetailReference):
        # Step 1: Initialize with listing data if available, creating a base dictionary.
        if detail_ref.listing_data:
            data_to_store = detail_ref.listing_data.to_flat_dict()
            # The key from listing is 'id', rename it to the canonical 'listing_id'
            if "id" in data_to_store:
                data_to_store["listing_id"] = data_to_store.pop("id")
        else:
            # For update mode or if listing data is missing, start with the ID.
            data_to_store = {"listing_id": detail_ref.house_id}

        # Step 2: Fetch and parse detail page data
        house_info = await self._fetch_and_parse_detail(detail_ref)

        if self.store:
            try:
                if house_info:
                    # Step 3: Merge detail data. This overwrites common fields (e.g., status)
                    # with more accurate data from the detail page and adds new fields.
                    detail_data = house_info.to_dict_items()
                    data_to_store.update(detail_data)

                    # Clean up the ID field after merge. The detail page's 'property_id'
                    # is the same as 'listing_id', so we can remove the redundant key.
                    if "property_id" in data_to_store:
                        del data_to_store["property_id"]

                    await self.store.store_listing(data_to_store)
                    self.snapshots_stored += 1
                else:
                    # Case: Total parsing failure, create a tombstone snapshot
                    logger.warning(
                        f"Creating tombstone snapshot for failed parse of house ID: {detail_ref.house_id}"
                    )
                    tombstone_data = {
                        "listing_id": detail_ref.house_id,
                        "status": "[PARSE_FAILED]",
                    }
                    await self.store.store_listing(tombstone_data)
                    self.tombstones_created += 1

            except Exception as e:
                logger.error(
                    f"Failed to store details or tombstone for house ID: {detail_ref.house_id}: {e}",
                    exc_info=True,
                )

    async def _fetch_and_parse_detail(
        self, detail: HouseDetailReference
    ) -> Optional[HouseDetail]:
        """
        Fetches and parses a single house detail page.
        Returns a tuple of (house_id, house_info object) or (None, None) on failure.
        """
        html_content = None
        async with self.semaphore:
            try:
                logger.debug(f"Fetching HTML for house ID: {detail.house_id}")

                uri_to_fetch = detail.detail_uri
                if "placeholder-city" in uri_to_fetch:
                    # Construct a generic URL that Funda can resolve with just the ID
                    uri_to_fetch = f"/en/zoek/object/?id={detail.house_id}"
                    logger.info(f"Using generic URL for update mode: {uri_to_fetch}")

                html_content = await self.playwright_client.get_house_detail_info(
                    uri_to_fetch
                )

                if not html_content:
                    logger.warning(
                        "Received empty HTML content for house ID: %s", detail.house_id
                    )
                    return None, None

                if "Je bent bijna op de pagina die je zoekt" in html_content:
                    raise IPBlockError("Captcha page detected.")

                house_info = await self._page_extractor.extract_details(
                    id=detail.house_id, page_content=html_content
                )

                if house_info is None:
                    logger.warning(
                        f"Parsing returned None for house ID: {detail.house_id}"
                    )
                    self.parsing_failures += 1
                    if html_content:
                        cleaned_html = utils.clean_html_content(html_content)
                        await utils.save_error_html(
                            city=detail.city,
                            house_id=detail.house_id,
                            html_content=cleaned_html,
                        )
                        self.error_html_saved += 1
                    return None

                # Check for partial failure (e.g., price is missing)
                essential_fields = ["price"]
                is_partial_failure = any(
                    getattr(house_info, field) is None for field in essential_fields
                )
                if is_partial_failure:
                    logger.warning(
                        f"Partial parsing failure for house ID: {detail.house_id}. Marking and preserving."
                    )
                    if html_content:
                        cleaned_html = utils.clean_html_content(html_content)
                        await utils.save_error_html(
                            city=detail.city,
                            house_id=detail.house_id,
                            html_content=cleaned_html,
                        )
                        self.error_html_saved += 1
                    original_description = house_info.description or ""
                    house_info.description = f"[PARTIAL_PARSE] {original_description}"

                return house_info

            except IPBlockError:
                logger.warning(
                    "IP blocked for house ID %s, reporting failure.", detail.house_id
                )
                self.ip_block_count += 1
                await self.cookie_manager.report_failure()
                if self.cookie_update_attempts < config.MAX_COOKIE_UPDATE_LIMIT:
                    self.cookie_update_attempts += 1
                    await self.cookie_manager.get_cookie(force_refresh=True)
                else:
                    raise Exception("Cookie update limit reached. Halting crawler.")

            except Exception as e:
                logger.error(
                    f"Failed to process detail for house [ID: {detail.house_id}]: {e}",
                    exc_info=True,
                )
                if html_content:
                    cleaned_html = utils.clean_html_content(html_content)
                    await utils.save_error_html(
                        city=detail.city,
                        house_id=detail.house_id,
                        html_content=cleaned_html,
                    )
                    self.error_html_saved += 1
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

    async def fetch_page(self, search_params: SearchParams):
        """
        Fetch and parse a single page of property listings with error handling.

        Args:
            search_params: SearchParams object containing all filter criteria.

        Returns:
            List of properties or empty list on error
        """
        page = search_params.page.from_
        logger.debug(f"Fetching page with 'from' parameter: {page}")
        try:
            current_page = await self.client.get_single_page_house_info(
                search_params=search_params
            )
            parsed_result = await self.client.parse_single_page_house_info(
                response_data=current_page, offering_type=search_params.offering_type
            )
            if parsed_result.properties:
                return parsed_result.properties

            logger.debug(f"Received 0 properties for 'from' parameter: {page}")
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

    async def get_house_info_generator(self):
        """
        An async generator that yields pages of property listings.
        """
        start_page = config.START_PAGE
        end_page = config.END_PAGE

        # Build initial search params for the first page
        search_params = self._build_search_params((start_page - 1) * 15)

        try:
            first_page_data = await self.client.get_single_page_house_info(
                search_params=search_params
            )
            first_page_houses = await self.client.parse_single_page_house_info(
                response_data=first_page_data,
                offering_type=search_params.offering_type,
            )
        except Exception as e:
            logger.error(f"Failed to fetch first page: {e}", exc_info=True)
            return

        yield first_page_houses.properties

        total_pages = math.ceil(first_page_houses.total_value / 15)
        logger.info(f"Total pages: {total_pages}")

        if end_page is None:
            end_page = total_pages + 1
        else:
            end_page = min(end_page, total_pages + 1)

        for page_num in range(start_page + 1, end_page):
            try:
                # THE FIX: Correctly calculate the 'from' parameter for pagination
                search_params.page.from_ = (page_num - 1) * 15
                page_properties = await self.fetch_page(search_params)
                yield page_properties
            except Exception as e:
                logger.error(f"Error fetching page {page_num}: {e}", exc_info=True)
                # Continue to the next page
                continue

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
                        "listing_id": house_id,  # Rename to match schema
                        "offering_type": config.OFFERING_TYPE,  # Add offering type
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

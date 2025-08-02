import asyncio
import copy
import logging
import json
import re
from typing import Callable, Dict, List, Optional, Union, Any
from urllib.parse import parse_qs, unquote, urlencode


import httpx
from box import Box
from lxml import etree
from httpx import Response
from tenacity import retry, stop_after_attempt, wait_fixed
from playwright.async_api import BrowserContext, Page

from tools import utils

from .exception import DataFetchError, PaginationLimitError, EmptyResponseError
from model.m_search import (
    SearchParamsCollection,
    SearchParams,
    PublicationDate,
    Page,
    OfferingType,
    Availability,
    ZoningType,
    ConstructionPeriod,
    EnergyLabel,
    PriceRange,
    Price,
)
from model.m_response import (
    PropertyResponse,
    Property,
    BuyProperty,
    BuyPropertyResponse,
)

logger = logging.getLogger("funda")


# from .field import SearchType


class FundaClient:
    def _format_search_params_for_logging(self, params: SearchParams) -> str:
        """Formats SearchParams into a concise, readable string for logging."""
        page_num = (params.page.from_ // 15) + 1
        return f"Fetching page {page_num} for '{params.offering_type.value}' in {params.selected_area}"

    def __init__(self, timeout=10, proxy=None, *, headers: Dict[str, str]):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.funda.nl"
        self._house_info_api_host = "https://listing-search-wonen.funda.io"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(
        self, method: str, url: str, response_type: str = "json", **kwargs
    ) -> Union[str, Dict[str, Any]]:

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code != 200:
            logger.error("request failed")
            logger.error(response.text)
            return

        if response_type:
            if response_type == "html":
                logger.info(response.text())
                return response.text
            elif response_type == "json":

                return response.json()

        else:  # 默认返回文本
            logger.info(response.text())
            return response.text

    async def post(self, uri: str, data: dict, headers=None, **kwargs) -> Dict:
        post_headers = headers if headers is not None else self.headers

        # json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        # json_str = "\n".join(json.dumps(item, separators=(",", ":")) for item in data)
        json_str = (
            "\n".join(json.dumps(item, separators=(",", ":")) for item in data) + "\n"
        )
        url = f"{self._house_info_api_host}{uri}"
        return await self.request(
            method="POST",
            url=url,
            data=json_str,
            headers=post_headers,
            **kwargs,
        )

    async def get_single_page_house_info(self, search_params: SearchParams) -> Dict:
        """
        Fetches a single page of house listings based on the provided search parameters.
        """
        uri = "/_msearch/template"

        # The page number is now managed inside the SearchParams object.
        # We just need to ensure the 'from' is calculated correctly before this call if needed,
        # but the core logic in FundaCrawler already handles this.

        # Format search areas to be compatible with Funda's API
        if search_params.selected_area:
            search_params.selected_area = [
                area.lower().replace(" ", "-") for area in search_params.selected_area
            ]

        # The SearchParams object is now the single source of truth.
        logger.info(self._format_search_params_for_logging(search_params))
        search_payload = SearchParamsCollection(base_params=search_params).to_list()

        return await self.post(uri, data=search_payload, response_type="json")

    async def parse_single_page_house_info(
        self, response_data, offering_type
    ) -> PropertyResponse:
        """
        Parse API response data into PropertyResponse objects with robust error handling.

        Args:
            response_data: Raw API response data
            offering_type: Type of offering (rent/buy)

        Returns:
            PropertyResponse: Parsed property data or empty response on error

        Raises:
            EmptyResponseError: When API returns invalid response structure
            PaginationLimitError: When pagination limit is exceeded
        """
        try:
            # Validate response data exists
            if not response_data:
                logger.error("Received empty response data")
                raise EmptyResponseError("API returned empty response data")

            data = Box(response_data, default_box=True, default_box_attr=None)

            # Validate response structure
            if not hasattr(data, "responses") or not data.responses:
                logger.error("Invalid response structure: missing 'responses' field")
                logger.debug("Response data structure: %s", response_data)
                raise EmptyResponseError(
                    "Invalid response structure: missing 'responses' field"
                )

            # Check if we have at least one response
            if len(data.responses) == 0:
                logger.error("Empty responses array in API response")
                raise EmptyResponseError("Empty responses array in API response")

            first_response = data.responses[0]

            # Critical fix: Check if hits exists and is not None
            if not hasattr(first_response, "hits") or first_response.hits is None:
                logger.error(
                    "No 'hits' field in API response - possible pagination limit exceeded"
                )
                logger.debug("First response structure: %s", first_response)

                # Check if this might be a pagination limit issue
                # Elasticsearch typically returns this structure when max_result_window is exceeded
                if hasattr(first_response, "error") or "error" in str(first_response):
                    raise PaginationLimitError(
                        "Search pagination limit exceeded. Try reducing page range or using more specific search criteria."
                    )
                else:
                    raise EmptyResponseError("API response missing 'hits' field")

            hits_data = first_response.hits

            # Validate hits structure
            if not hasattr(hits_data, "total") or hits_data.total is None:
                logger.error("Invalid hits structure: missing 'total' field")
                raise EmptyResponseError(
                    "Invalid hits structure: missing 'total' field"
                )

            if not hasattr(hits_data, "hits") or hits_data.hits is None:
                logger.warning("No property listings found in response")
                # Return empty response with total info if available
                total_value = (
                    getattr(hits_data.total, "value", 0)
                    if hasattr(hits_data.total, "value")
                    else 0
                )
                total_relation = (
                    getattr(hits_data.total, "relation", "eq")
                    if hasattr(hits_data.total, "relation")
                    else "eq"
                )

                if offering_type == OfferingType.rent:
                    return PropertyResponse(
                        total_value=total_value,
                        total_relation=total_relation,
                        properties=[],
                    )
                else:
                    return BuyPropertyResponse(
                        total_value=total_value,
                        total_relation=total_relation,
                        properties=[],
                    )

            total = hits_data.total
            listings = hits_data.hits

            logger.debug(
                "Processing %d property listings from API response", len(listings)
            )

            properties = []
            for hit in listings:
                try:
                    if not hasattr(hit, "_source") or hit._source is None:
                        logger.warning("Skipping hit with missing '_source' field")
                        continue

                    source = hit._source

                    # Create Property object using Pydantic
                    if offering_type == OfferingType.rent:
                        property_obj = Property(
                            id=source.id,
                            property_type=source.object_type,
                            type=source.type,
                            status=source.status,
                            zoning=source.zoning,
                            construction_type=source.construction_type,
                            floor_area=source.floor_area,
                            floor_area_range=source.floor_area_range,
                            plot_area=source.plot_area,
                            plot_area_range=source.plot_area_range,
                            number_of_rooms=source.number_of_rooms,
                            number_of_bedrooms=source.number_of_bedrooms,
                            energy_label=source.energy_label,
                            price=source.price,
                            offering_type=source.offering_type,
                            address=source.address,
                            agent=source.agent,
                            thumbnail_id=source.thumbnail_id,
                            available_media_types=source.available_media_types,
                            detail_page_relative_url=source.object_detail_page_relative_url,
                            publish_date=source.publish_date,
                            blikvanger=source.blikvanger,
                        )
                    else:
                        property_obj = BuyProperty(
                            id=source.id,
                            property_type=source.object_type,
                            type=source.type,
                            status=source.status,
                            zoning=source.zoning,
                            construction_type=source.construction_type,
                            floor_area=source.floor_area,
                            floor_area_range=source.floor_area_range,
                            plot_area=source.plot_area,
                            plot_area_range=source.plot_area_range,
                            number_of_rooms=source.number_of_rooms,
                            number_of_bedrooms=source.number_of_bedrooms,
                            energy_label=source.energy_label,
                            price=source.price,
                            offering_type=source.offering_type,
                            address=source.address,
                            agent=source.agent,
                            thumbnail_id=source.thumbnail_id,
                            available_media_types=source.available_media_types,
                            detail_page_relative_url=source.object_detail_page_relative_url,
                            publish_date=source.publish_date,
                            blikvanger=source.blikvanger,
                        )
                    properties.append(property_obj)
                except Exception as e:
                    logger.error(
                        "Failed to parse property [ID: %s]: %s",
                        getattr(hit, "_id", "unknown"),
                        str(e),
                        exc_info=True,
                        extra={
                            "source_data": getattr(hit, "_source", None),
                            "error_type": type(e).__name__,
                        },
                    )
                    continue

            logger.debug(
                "Successfully parsed %d out of %d properties",
                len(properties),
                len(listings),
            )

            # Create and return appropriate response object
            if offering_type == OfferingType.rent:
                return PropertyResponse(
                    total_value=total.value,
                    total_relation=total.relation,
                    properties=properties,
                )
            else:
                return BuyPropertyResponse(
                    total_value=total.value,
                    total_relation=total.relation,
                    properties=properties,
                )

        except (PaginationLimitError, EmptyResponseError):
            # Re-raise specific exceptions to be handled by caller
            raise
        except Exception as e:
            logger.error("Failed to parse property data: %s", str(e), exc_info=True)
            logger.debug("Raw response data: %s", response_data)

            # Return empty response instead of crashing
            if offering_type == OfferingType.rent:
                return PropertyResponse(
                    total_value=0, total_relation="eq", properties=[]
                )
            else:
                return BuyPropertyResponse(
                    total_value=0, total_relation="eq", properties=[]
                )


class FundaPlaywrightClient:
    def __init__(
        self,
        timeout=10,
        proxies=None,
        *,
        headers: Dict[str, str],
        playwright_page: Page,
        cookie_dict: Dict[str, str],
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.funda.nl/en"
        self._house_info_api_host = "https://listing-search-wonen.funda.io"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        # self._image_agent_host = "https://i1.wp.com/"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(
        self, method: str, url: str, response_type: str = "json", **kwargs
    ) -> Union[str, Dict[str, Any]]:

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code != 200:
            logger.error("request failed")
            logger.error(response.text)
            return

        if response_type:
            if response_type == "html":
                return response.text
            elif response_type == "json":
                return response.json()

        else:
            return response.text

    async def get(
        self, uri: str, params=None, headers=None, **kwargs
    ) -> Union[Response, etree._Element]:
        url = self._host + uri  # Combine host and URI *only* here
        logger.debug("fetching %s", url)

        if params:
            url += "?" + urlencode(params)  # More concise way to add parameters

        get_headers = headers if headers is not None else self.headers

        return await self.request(method="GET", url=url, headers=get_headers, **kwargs)

    async def post(self, uri: str, data: dict, headers=None, **kwargs) -> Dict:
        post_headers = headers if headers is not None else self.headers

        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

        url = f"{self._house_info_api_host}{uri}"
        return await self.request(
            method="POST",
            url=url,
            data=json_str,
            headers=post_headers,
            **kwargs,
        )

    async def update_cookies(self, browser_context: BrowserContext):
        cookie_str, cookie_dict = utils.convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def get_house_detail_info(self, uri):
        try:
            response = await self.get(uri, response_type="html")
            return response
        except Exception as e:
            logger.error(
                "Error fetching house detail for %s: %s", uri, str(e), exc_info=True
            )
            return None

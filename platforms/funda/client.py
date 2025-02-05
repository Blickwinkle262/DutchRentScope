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

from .exception import DataFetchError
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
                return response.text
            elif response_type == "json":
                return response.json()

        else:  # 默认返回文本
            return response.text

    async def post(self, uri: str, data: dict, headers=None, **kwargs) -> Dict:
        post_headers = headers if headers is not None else self.headers

        # json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        # json_str = "\n".join(json.dumps(item, separators=(",", ":")) for item in data)
        json_str = (
            "\n".join(json.dumps(item, separators=(",", ":")) for item in data) + "\n"
        )
        url = f"{self._house_info_api_host}{uri}"
        logger.debug(url)
        return await self.request(
            method="POST",
            url=url,
            data=json_str,
            headers=post_headers,
            **kwargs,
        )

    async def get_single_page_house_info(
        self,
        selected_area: List[str],
        offering_type: OfferingType,
        price_range: PriceRange,
        page: int = 1,
        free_text_search: str = "",
        energy_labels: List[EnergyLabel] = None,
        availability: Optional[List[Availability]] = None,
        publication_date: PublicationDate = PublicationDate.NO_PREFERENCE,
        zoning: Optional[List[ZoningType]] = None,
        construction_period: Optional[List[ConstructionPeriod]] = None,
    ) -> Dict:
        """
        pass
        """
        uri = "/_msearch/template"

        from_index = (page - 1) * 15
        if offering_type == OfferingType.rent:
            price = Price(rent_price=price_range)
        elif offering_type == OfferingType.buy:
            price = Price(selling_price=price_range)
        else:
            price = None

        base_params = SearchParams(
            selected_area=selected_area,
            offering_type=offering_type,
            publication_date=publication_date,
            availability=availability,
            free_text_search=free_text_search,
            page=Page(from_=from_index),
            construction_period=construction_period,
            zoning=zoning,
            energy_labels=energy_labels,
            price=price,
        )

        search_params = SearchParamsCollection(base_params=base_params).to_list()
        logger.debug(f"construct search_params {search_params}")

        return await self.post(uri, data=search_params, response_type="json")

    async def parse_single_page_house_info(
        self, response_data, offering_type
    ) -> PropertyResponse:

        try:
            data = Box(response_data, default_box=True, default_box_attr=None)

            # Get first response's hits using attribute access
            hits_data = data.responses[0].hits
            total = hits_data.total
            listings = hits_data.hits

            properties = []
            for hit in listings:
                try:
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
                        "Failed to parse property [ID: %s]",
                        hit.get("_id", "unknown"),
                        exc_info=True,
                        extra={"source_data": source, "error_type": type(e).__name__},
                    )
                    continue
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

        except Exception as e:
            logger.error("Failed to parse property data: %s", str(e), exc_info=True)
            return PropertyResponse()


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
        logger.info("fetching %s", url)

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

    async def get_house_detail_info(self, uri, semaphore):
        async with semaphore:
            try:
                response = await self.get(uri, response_type="html")
                return response
            except Exception as e:
                logger.error(
                    "Error fetching house detail for %s: %s", uri, str(e), exc_info=True
                )
                return None

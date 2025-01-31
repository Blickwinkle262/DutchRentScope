import html
import json
import re
from typing import Dict, List, Tuple, Any

from parsel import Selector

from model.m_house_detail import HouseDetails


class FundaDetailExtractor:
    def __init__(self):
        pass

    @staticmethod
    async def extract_details(page_content: str) -> HouseDetails:
        selector = Selector(text=page_content)
        house_details = {}

        xpath_mappings = {
            "price": "//div[@class='flex flex-col text-xl']/div/text()",
            "deposit": "//dt[contains(text(), 'Deposit')]/following-sibling::dd[1]/text()",
            "living_area": """(
                //li[.//svg[contains(@viewBox, '48')]]/span[@class='md:font-bold']/text()
                |
                //dt[contains(text(), 'Living area')]/following-sibling::dd[1]/text()
            )[1]""",
            "external_area": "//dt[contains(text(), 'Exterior space attached to the building')]/following-sibling::dd[1]/text()",
            "volume": "//dt[contains(text(), 'Volume in cubic meters')]/following-sibling::dd[1]/text()",
            "construction_year": "//dt[contains(text(), 'Year of construction')]/following-sibling::dd[1]/text()",
            "house_type": "//dt[contains(text(), 'Type apartment')]/following-sibling::dd[1]/text()",
            "energy_label": "//span[contains(@class, 'inline-block px-2 text-center text-white')]/text()",
            "balcony": "//dt[contains(text(), 'Balcony/roof terrace')]/following-sibling::dd[1]/text()",
            "storage": "//dt[contains(text(), 'Shed / storage')]/following-sibling::dd[1]/text()",
            "parking": "//dt[contains(text(), 'Type of parking facilities')]/following-sibling::dd[1]/text()",
            "status": "//dt[contains(text(), 'Status')]/following-sibling::dd[1]/text()",
            "insulation": """normalize-space(
                //dt[contains(text(), 'Insulation')]/following-sibling::dd[1]/text()
            )""",
            "heating": """normalize-space(
                //dt[contains(text(), 'Heating')]/following-sibling::dd[1]/text()
            )""",
            "hot_water": """normalize-space(
                //dt[contains(text(), 'Hot water')]/following-sibling::dd[1]/text()
            )""",
        }

        for field, xpath in xpath_mappings.items():
            house_details[field] = selector.xpath(xpath).get()
        description = selector.xpath(
            "//div[@data-headlessui-state and contains(@class,'listing-description-text')]/text()"
        ).getall()
        if not description:
            description = selector.xpath("//meta[@name='description']/@content").get()

        house_details["description"] = (
            " ".join(description).strip()
            if isinstance(description, list)
            else description or ""
        )

        return HouseDetails(**house_details)

    @staticmethod
    def clean_xpath_result(selector_result, default=""):
        return selector_result.get() if selector_result else default

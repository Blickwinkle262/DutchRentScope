import html
import json
import re
from typing import Dict, List, Tuple, Any

from parsel import Selector

from config.base_config import funda_rules, funda_detail_rules
from model.funda import RentInfo


class FundaExtractor:
    def __init__(self):
        self._validate_rules()

    def _validate_rules(self):
        """validate xpath rules cover RentInfo needed field"""

        required_fields = RentInfo.to_dict().keys()
        configured_fields = set(funda_rules.keys())
        missing_fields = required_fields - configured_fields

        if missing_fields:
            raise ValueError(
                f"Missing required fields in funda_rules: {missing_fields}"
            )

    def extract_basic_info(self, page_content: str) -> List[RentInfo]:
        result: List[RentInfo] = []
        house_info_xpath_selector = "//div[contains(@class, 'border-b pb-3')]"
        # TODO: make the house_info_xpath into config
        house_list = Selector(text=page_content).xpath(house_info_xpath_selector)
        for house in house_list:
            house_info = {}
            for field in RentInfo.to_dict().values():
                data = house.xpath(funda_rules.get(field))
                house_info[field] = data
            rent_info = RentInfo(**data)
            result.append(rent_info)
        return result

    def extract_detail(self, page_content: str):
        pass

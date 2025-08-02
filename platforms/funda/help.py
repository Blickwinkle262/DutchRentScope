# help.py
import json
import logging
from pathlib import Path
from parsel import Selector
from typing import Optional
from model.m_house_detail import HouseDetail

logger = logging.getLogger("funda")


def is_parseable_listing(selector: Selector) -> bool:
    """
    Performs a pre-check on the HTML to determine if it's a standard, parseable listing.
    Filters out non-residential properties, projects, and listings with price ranges.
    """
    title = selector.xpath("//title/text()").get(default="").lower()
    non_residential_keywords = ["parking", "garage", "bouwgrond", "project"]
    if any(keyword in title for keyword in non_residential_keywords):
        return False

    price_text = selector.xpath(
        "//div[contains(@class, 'flex-col text-xl')]//*[contains(text(), '€')]/text()"
    ).get(default="")
    if "to" in price_text or "Prijzen op aanvraag" in price_text:
        return False

    return True


class BaseFundaDetailExtractor:
    """
    基类，负责加载XPath配置并根据房源状态动态执行提取逻辑。
    """

    def __init__(self, config_path: Path, extractor_type: str):
        self.extractor_type = extractor_type
        with open(config_path, "r") as f:
            # 加载特定类型的所有配置（包括common, available, rented等）
            self.config = json.load(f)[self.extractor_type]
        logger.info(
            f"Initialized {self.__class__.__name__} with '{self.extractor_type}' configurations."
        )

    async def extract_details(
        self, id: str, page_content: str
    ) -> Optional[HouseDetail]:
        selector = Selector(text=page_content)

        if not is_parseable_listing(selector):
            logger.info(
                f"Skipping non-parseable property [ID: {id}] based on pre-check."
            )
            return None

        house_details = {}
        logger.debug(f"Starting house details extraction for ID: {id}")

        # 1. 首先，检查房源状态
        status_xpath = self.config.get("status_check_xpath")
        status_text = "available"  # Default to available
        if status_xpath:
            status_text = (
                selector.xpath(status_xpath).get(default="available").strip().lower()
            )

        house_details["status"] = status_text.capitalize()

        # 2. 根据状态动态构建最终的XPath映射
        xpath_mappings = self.config["common"].copy()
        if "available" in status_text:
            xpath_mappings.update(self.config["available"])
            logger.debug(
                f"Property ID {id} is Available. Using 'available' specific XPaths."
            )
        elif "rented" in status_text or "sold" in status_text:
            state_key = "rented" if "rented" in status_text else "sold"
            if state_key in self.config:
                xpath_mappings.update(self.config[state_key])
                logger.debug(
                    f"Property ID {id} is {state_key}. Using '{state_key}' specific XPaths."
                )
        else:  # 如果状态未知或为空，可以尝试使用 available 作为默认
            if "available" in self.config:
                xpath_mappings.update(self.config["available"])
                logger.warning(
                    f"Property ID {id} has an unknown status ('{status_text}'). Defaulting to 'available' XPaths."
                )

        # 3. 循环提取所有适用的字段
        for field, xpath in xpath_mappings.items():
            # 确保不重复提取已经获取的状态字段
            if field != "status":
                house_details[field] = selector.xpath(xpath).get()

        # 描述的提取逻辑保持不变
        description_parts = selector.xpath(
            "//div[@data-headlessui-state and contains(@class,'listing-description-text')]/descendant::*/text()"
        ).getall()
        description = " ".join(
            part.strip() for part in description_parts if part.strip()
        )
        if not description:
            description = selector.xpath("//meta[@name='description']/@content").get()
        house_details["description"] = description or ""

        try:
            return HouseDetail(id=id, **house_details)
        except Exception as e:
            logger.error(f"Failed to instantiate HouseDetail for ID {id}: {e}")
            logger.error(f"Data passed to constructor: {house_details}")
            return None


class FundaBuyExtractor(BaseFundaDetailExtractor):
    """专门用于提取购买房源信息的类"""

    def __init__(self, config_path: Path = Path("config/config_xpaths.json")):
        super().__init__(config_path, "buy")


class FundaRentExtractor(BaseFundaDetailExtractor):
    """专门用于提取租赁房源信息的类"""

    def __init__(self, config_path: Path = Path("config/config_xpaths.json")):
        super().__init__(config_path, "rent")

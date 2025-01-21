import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Union, Dict, Any, Generator


from urllib.parse import urlencode, quote_plus

from config.base_config import search_date


class SearchType(Enum):
    RENT = "huur"
    BUY = "koop"


class EnergyLabel(str, Enum):
    # 正确的URL编码格式
    A_PLUS_5 = "A+++++"
    A_PLUS_4 = "A++++"
    A_PLUS_3 = "A+++"
    A_PLUS_2 = "A++"
    A_PLUS_1 = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class ObjectType(str, Enum):
    HOUSE = "house"
    APARTMENT = "apartment"
    PARKING = "parking"
    LAND = "land"


class Availability(str, Enum):
    AVAILABLE = "available"
    NEGOTIATIONS = "negotiations"
    UNAVAILABLE = "unavailable"


class ExteriorSpaceType(str, Enum):
    BALCONY = "balcony"
    TERRACE = "terrace"
    GARDEN = "garden"


class GardenOrientation(str, Enum):
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"


# Age of Property on the web
class ConstructionPeriod(str, Enum):
    BEFORE_1906 = "before_1906"
    FROM_1906_TO_1930 = "from_1906_to_1930"
    FROM_1931_TO_1944 = "from_1931_to_1944"
    FROM_1945_TO_1959 = "from_1945_to_1959"
    FROM_1960_TO_1970 = "from_1960_to_1970"
    FROM_1971_TO_1980 = "from_1971_to_1980"
    FROM_1981_TO_1990 = "from_1981_to_1990"
    FROM_1991_TO_2000 = "from_1991_to_2000"
    FROM_2001_TO_2010 = "from_2001_to_2010"
    FROM_2011_TO_2020 = "from_2011_to_2020"
    AFTER_2020 = "after_2020"
    UNKNOWN = "unknown"

    @classmethod
    def parse_years(
        cls, start_year: int, end_year: Optional[int] = None
    ) -> Union[List["ConstructionPeriod"], "ConstructionPeriod"]:
        """根据开始年份和可选的结束年份返回对应的建筑时期"""
        if end_year is None:
            # 单一年份判断
            if start_year < 1906:
                return cls.BEFORE_1906
            elif start_year > 2020:
                return cls.AFTER_2020

            for period in cls:
                if period in [cls.BEFORE_1906, cls.AFTER_2020, cls.UNKNOWN]:
                    continue

                # 解析时期的年份范围
                period_str = period.value
                if period_str.startswith("from_"):
                    period_start = int(period_str.split("_to_")[0].split("from_")[1])
                    period_end = int(period_str.split("_to_")[1])
                    if period_start <= start_year <= period_end:
                        return period

            return cls.UNKNOWN
        else:
            # 处理年份范围，返回所有符合的时期
            periods = []
            for year in range(start_year, end_year + 1):
                period = cls.parse_years(year)
                if period not in periods:
                    periods.append(period)
            return periods


@dataclass
class FundaSearchParams:
    # Required parameters
    search_type: SearchType = field(default=SearchType.RENT)
    selected_area: str = field(default=None)
    # Optional parameters - 使用 None 作为默认值
    price_range: Optional[tuple[int, int]] = field(default=None)
    object_types: Optional[List[ObjectType]] = field(default=None)
    availability_types: Optional[List[Availability]] = field(default=None)
    floor_area: Optional[tuple[int, int]] = field(default=None)
    energy_labels: Optional[List[EnergyLabel]] = field(default=None)
    exterior_space_types: Optional[List[ExteriorSpaceType]] = field(default=None)
    garden_orientations: Optional[List[GardenOrientation]] = field(default=None)
    construction_period: Optional[List[ConstructionPeriod]] = field(default=None)

    def to_dict(self) -> dict:
        params = {}

        if self.selected_area:
            params["selected_area"] = quote_plus(json.dumps([self.selected_area]))

        if self.price_range:
            params["price"] = quote_plus(f"{self.price_range[0]}-{self.price_range[1]}")

        if self.object_types:
            params["object_type"] = json.dumps(
                [t.value for t in self.object_types]
            )  # Use json.dumps

        if self.availability_types:
            params["availability"] = json.dumps(
                [a.value for a in self.availability_types]
            )  # Use json.dumps

        if self.floor_area:
            params["floor_area"] = f"{self.floor_area[0]}-{self.floor_area[1]}"

        if self.energy_labels:
            params["energy_label"] = json.dumps(
                [label.value for label in self.energy_labels]
            )  # Use json.dumps

        if self.exterior_space_types:
            params["exterior_space_type"] = json.dumps(
                [t.value for t in self.exterior_space_types]
            )  # Use json.dumps

        if self.garden_orientations:
            params["exterior_space_garden_orientation"] = json.dumps(
                [o.value for o in self.garden_orientations]
            )  # Use json.dumps

        return params


class SearchTypeId(Enum):
    # basic info
    SEARCH_RESULT = "search_result"
    OBJECT_TYPE = "object_type"
    OBJECT_TYPE_HOUSE_ORIENTATION = "object_type_house_orientation"
    OBJECT_TYPE_HOUSE = "object_type_house"
    OBJECT_TYPE_APARTMENT_ORIENTATION = "object_type_apartment_orientation"
    OBJECT_TYPE_APARTMENT = "object_type_apartment"
    OBJECT_TYPE_PARKING = "object_type_parking"
    OBJECT_TYPE_PARKING_CAPACITY = "object_type_parking_capacity"
    # availability
    PUBLICATION_DATE = "publication_date"
    AVAILABILITY = "availability"
    RENTAL_AGREEMENT = "rental_agreement"
    # property
    ENERGY_LABEL = "energy_label"
    EXTERIOR_SPACE_TYPE = "exterior_space_type"
    EXTERIOR_SPACE_GARDEN_ORIENTATION = "exterior_space_garden_orientation"
    CONSTRUCTION_TYPE = "construction_type"
    ZONING = "zoning"
    CONSTRUCTION_PERIOD = "construction_period"
    # location
    SURROUNDING = "surrounding"
    PARKING_FACILITY = "parking_facility"
    GARAGE_TYPE = "garage_type"
    ACCESSIBILITY = "accessibility"
    AMENITIES = "amenities"
    TYPE = "type"
    OPEN_HOUSE = "open_house"

    def get_request_id(self, search_date: str = search_date) -> str:
        return f"{self.value}_{search_date}"


class PropertyType(Enum):
    house = "house"
    apartment = "apartment"
    parking = "parking"
    land = "land"


class PublicationDate(str, Enum):
    NO_PREFERENCE = "no_preference"
    TODAY = "1"
    THREE_DAYS = "3"
    FIVE_DAYS = "5"
    TEN_DAYS = "10"

    def to_dict(self) -> Dict[str, bool]:

        return {self.value: True}

    @property
    def days(self) -> Optional[int]:

        return None if self == self.NO_PREFERENCE else int(self.value)


@dataclass
class Page:
    from_: int

    def to_dict(self) -> Dict[str, Any]:
        return {"from": self.from_}


@dataclass
class Sort:
    field: str = "relevancy_sort_order"
    order: str = "desc"
    offering_type: str = "both"
    old_option: str = "relevance"


class OffereingType(str, Enum):
    rent = "rent"
    buy = "buy"


class ZoningType(str, Enum):
    recreational = "recreational"
    residential = "residential"


@dataclass
class SearchParams:

    selected_area: Optional[List[str]]
    offering_type: OffereingType

    free_text_search: str
    page: Page

    type: List[str] = field(default_factory=lambda: ["single"])
    sort: Sort = field(default_factory=Sort)
    open_house: Dict = field(default_factory=dict)
    publication_date: Optional[PublicationDate] = None
    object_type: Optional[List[str]] = None
    zoning: Optional[List[ZoningType]] = None
    availability: Optional[List[Availability]] = None
    construction_period: Optional[List[ConstructionPeriod]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为API所需的字典格式"""
        result = asdict(self)

        # Special handling for publication_date and Page
        if self.publication_date:
            result["publication_date"] = self.publication_date.to_dict()
        result["page"] = self.page.to_dict()

        result = {
            k: (
                [item.value for item in v]
                if isinstance(v, list) and v and isinstance(v[0], Enum)
                else v
            )
            for k, v in result.items()
        }
        # remove None key pairs
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class SearchItem:
    """单个搜索请求项，包含 index 声明和请求体"""

    index_line: Dict[str, str]
    body: Dict[str, Any]

    @classmethod
    def create(
        cls, search_type: SearchTypeId, params: SearchParams, search_date=search_date
    ) -> "SearchItem":
        index_line = {"index": "listings-wonen-searcher-alias-prod"}
        body = {
            "id": search_type.get_request_id(search_date),
            "params": params.to_dict(),
        }
        return cls(index_line=index_line, body=body)

    def to_list(self) -> List[Dict[str, Any]]:

        return [self.index_line, self.body]


@dataclass
class SearchParamsCollection:

    base_params: SearchParams

    search_date: str = search_date
    search_types: List[SearchTypeId] = None

    def __post_init__(self):
        if self.search_types is None:
            self.search_types = list(SearchTypeId)

    def generate_items(self) -> Generator[SearchItem, None, None]:
        for search_type in SearchTypeId:
            yield SearchItem.create(
                search_type=search_type,
                search_date=self.search_date,
                params=self.base_params,
            )

    def to_list(self) -> List[Dict[str, Any]]:
        result = []
        for item in self.generate_items():
            result.extend(item.to_list())
        return result

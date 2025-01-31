from datetime import datetime
from typing import List, Optional, Any, Dict


from box import Box
from pydantic import BaseModel, Field, conlist


class PriceRange(BaseModel):
    gte: float = Field(default=0.0)  # Greater than or equal
    lte: float = Field(default=0.0)  # Less than or equal


class Price(BaseModel):
    rent_price: List[float] = Field(default_factory=list)
    rent_price_condition: str = Field(default="per_month")
    rent_price_range: PriceRange = Field(default_factory=PriceRange)
    rent_price_type: str = Field(default="regular")


class AreaRange(BaseModel):
    gte: float = Field(default=0.0)
    lte: float = Field(default=0.0)


class Address(BaseModel):
    country: str = Field(default="")
    province: str = Field(default="")
    city: str = Field(default="")
    municipality: str = Field(default="")
    wijk: str = Field(default="")  # District
    neighbourhood: str = Field(default="")
    street_name: str = Field(default="")
    house_number: str = Field(default="")
    house_number_suffix: Optional[str] = Field(default=None)
    postal_code: str = Field(default="")
    identifiers: List[str] = Field(default_factory=list)
    is_bag_address: bool = Field(default=False)


class Agent(BaseModel):
    id: int = Field(default=0)
    name: str = Field(default="")
    association: str = Field(default="")  # e.g., "VBO", "NVM"
    logo_type: str = Field(default="")
    logo_id: int = Field(default=0)
    relative_url: str = Field(default="")
    is_primary: bool = Field(default=False)


class Blikvanger(BaseModel):
    enabled: bool = Field(default=False)


class Property(BaseModel):
    # Basic information
    id: int = Field(default=0)
    property_type: str = Field(default="")  # e.g., "apartment", "house"
    type: str = Field(default="")  # e.g., "single"
    status: str = Field(default="")
    zoning: str = Field(default="")  # e.g., "residential"
    construction_type: None | str = None  # e.g., "newly_built", "resale"

    # Areas
    floor_area: List[float] | None = Field(default=None)
    floor_area_range: AreaRange | None = Field(default=None)
    plot_area: List[float] = Field(default_factory=list)
    plot_area_range: AreaRange = Field(default_factory=AreaRange)

    # Rooms and specifications
    number_of_rooms: int | None = Field(default=None)
    number_of_bedrooms: int | None = Field(default=None)
    energy_label: str = Field(default="unknown")

    # Price and offering
    price: Price = Field(default_factory=Price)
    offering_type: List[str] = Field(default_factory=list)

    # Location and agent
    address: Address = Field(default_factory=Address)
    agent: List[Agent] = Field(default_factory=list)

    # Media and URLs
    thumbnail_id: List[int] = Field(default_factory=list)
    available_media_types: List[str] = Field(default_factory=list)
    detail_page_relative_url: str = Field(default="")

    # Metadata
    publish_date: str = Field(default="")
    blikvanger: Blikvanger = Field(default_factory=Blikvanger)

    def to_flat_dict(self) -> Dict:
        """Convert Property object to a flat dictionary structure"""
        base_dict = {
            # Basic information
            "id": self.id,
            "property_type": self.property_type,
            "type": self.type,
            "status": self.status,
            "zoning": self.zoning,
            "construction_type": self.construction_type,
            # Areas
            "floor_area": self.floor_area[0] if self.floor_area else None,
            "plot_area": self.plot_area[0] if self.plot_area else None,
            # Area ranges
            "floor_area_range_min": (
                self.floor_area_range.gte if self.floor_area_range else None
            ),
            "floor_area_range_max": (
                self.floor_area_range.lte if self.floor_area_range else None
            ),
            "plot_area_range_min": self.plot_area_range.gte,
            "plot_area_range_max": self.plot_area_range.lte,
            # Rooms and specs
            "number_of_rooms": self.number_of_rooms,
            "number_of_bedrooms": self.number_of_bedrooms,
            "energy_label": self.energy_label,
            # Price
            "rent_price": self.price.rent_price[0] if self.price.rent_price else None,
            "rent_price_condition": self.price.rent_price_condition,
            "rent_price_type": self.price.rent_price_type,
            "rent_price_range_min": self.price.rent_price_range.gte,
            "rent_price_range_max": self.price.rent_price_range.lte,
            # Address
            "address_country": self.address.country,
            "address_province": self.address.province,
            "address_city": self.address.city,
            "address_municipality": self.address.municipality,
            "address_district": self.address.wijk,
            "address_neighbourhood": self.address.neighbourhood,
            "address_street": self.address.street_name,
            "address_number": self.address.house_number,
            "address_suffix": self.address.house_number_suffix,
            "address_postal_code": self.address.postal_code,
            "address_is_bag": self.address.is_bag_address,
            # Agent (first agent if exists)
            "agent_name": self.agent[0] if self.agent else None,
            # Media and URLs
            "detail_url": self.detail_page_relative_url,
            "media_types": (
                ",".join(self.available_media_types)
                if self.available_media_types
                else ""
            ),
            # Metadata
            "publish_date": self.publish_date,
            "blikvanger_enabled": self.blikvanger.enabled,
        }

        # 添加当前时间戳
        base_dict["crawl_date"] = datetime.now().isoformat()

        return base_dict

    def to_nested_dict(self) -> Dict:
        """Convert to nested dictionary structure (using model_dump)"""
        return self.model_dump()


class PropertyResponse(BaseModel):
    total_value: int = Field(default=0)
    total_relation: str = Field(default="eq")
    properties: List[Property] = Field(default_factory=list)

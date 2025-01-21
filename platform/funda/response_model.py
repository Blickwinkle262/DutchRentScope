from pydantic import BaseModel, Field, conlist
from typing import List, Optional, Any
from datetime import datetime
import json
from box import Box


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
    object_type: str = Field(default="")  # e.g., "apartment", "house"
    type: str = Field(default="")  # e.g., "single"
    status: str = Field(default="")
    zoning: str = Field(default="")  # e.g., "residential"
    construction_type: str = Field(default="")  # e.g., "newly_built", "resale"

    # Areas
    floor_area: List[float] = Field(default_factory=list)
    floor_area_range: AreaRange = Field(default_factory=AreaRange)
    plot_area: List[float] = Field(default_factory=list)
    plot_area_range: AreaRange = Field(default_factory=AreaRange)

    # Rooms and specifications
    number_of_rooms: int = Field(default=0)
    number_of_bedrooms: int = Field(default=0)
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
    object_detail_page_relative_url: str = Field(default="")

    # Metadata
    publish_date: str = Field(default="")
    blikvanger: Blikvanger = Field(default_factory=Blikvanger)


class PropertyResponse(BaseModel):
    total_value: int = Field(default=0)
    total_relation: str = Field(default="eq")
    properties: List[Property] = Field(default_factory=list)

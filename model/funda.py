from typing import Optional


class ItemDescriptor:
    def __init__(self, field_type=str, pipeline_func=None):
        self.field_type = field_type
        if pipeline_func is None:
            pipeline_func = lambda self, x: x
        self.pipeline_func = pipeline_func

    def __set_name__(self, owner, name):
        self.name = name
        self._private_name = f"_{name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = instance.__dict__.get(self._private_name, None)

        if value is None:
            return 0 if self.field_type in (int, float) else ""
        else:
            try:
                value = self.pipeline_func(instance, value)
                return self.field_type(value)
            except (ValueError, TypeError):
                return 0 if self.field_type in (int, float) else ""

    def __set__(self, instance, value):
        instance.__dict__[self._private_name] = value

    def __call__(self, pipeline_func):
        self.pipeline_func = pipeline_func
        return self


class RentInfo:

    @ItemDescriptor(float)
    def monthly_rent(self, value):
        return value.replace("€", "").replace(",", "").split("/")[0].strip()

    @ItemDescriptor(int)
    def living_area(self, value):
        return value.replace("m²", "").strip()

    @ItemDescriptor(int)
    def bedroom_count(self, value):
        return value.strip()

    @ItemDescriptor(str)
    def energy_level(self, value):
        level = value.strip().upper()
        return level if level in "ABCDEFG" else ""

    @ItemDescriptor(str)
    def street_address(self, value):
        return value

    @ItemDescriptor(str)
    def postal_code(self, value):
        return value.strip()

    @ItemDescriptor(str)
    def city(self, value):
        return value.strip()

    @ItemDescriptor(str)
    def property_agent(self, value):
        return value

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, f"_{key}", value)

    @classmethod
    def to_dict(cls):
        return {
            name: getattr(cls, name)
            for name in cls.__dict__
            if not name.startswith("_")
            and isinstance(getattr(cls, name), ItemDescriptor)
        }


# class RentInfo(BaseModel):
#     monthly_rent: float = Field(..., description="monthly rent price")
#     living_area: int = Field(..., description="m2 area for living")
#     bedroom_count: int = Field(..., description="number of bedrooms")
#     energy_level: str = Field(..., description="energy efficiency range from A to G")
#     street_address: str = Field(..., description="")
#     postal_code: str = Field(..., description="")
#     city: str = Field(..., description="")
#     property_agent: str = Field(..., description="real estate agency")
class HouseDetails:
    pass

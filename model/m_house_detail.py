import re
from typing import Dict, Any


# This is the descriptor class that powers the cleaning logic.
# It's used as a decorator.
class ItemDescriptor:
    def __init__(self, target_type):
        self.target_type = target_type
        self.func = None

    def __call__(self, func):
        self.func = func
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return self

        raw_value = getattr(instance, "_" + self.func.__name__, None)
        return self.func(instance, raw_value)

    def __set__(self, instance, value):
        setattr(instance, "_" + self.func.__name__, value)


class HouseDetail:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            # This allows initializing with 'id' from the extractor
            if key == "id":
                key = "property_id"
            setattr(self, key, value)

    def _clean_numeric(self, value: str, is_int: bool = False) -> Any:
        """A helper to clean numeric strings."""
        if not isinstance(value, str):
            return value
        try:
            # Remove currency, separators, units, and text
            cleaned = re.sub(r"[€.,\sA-Za-z/²³]+", "", value)
            if not cleaned:
                return None
            return int(cleaned) if is_int else float(cleaned)
        except (ValueError, TypeError):
            return None

    @ItemDescriptor(int)
    def property_id(self, value):
        return int(value) if value else None

    @ItemDescriptor(float)
    def price(self, value):
        return self._clean_numeric(value)

    @ItemDescriptor(float)
    def deposit(self, value):
        return self._clean_numeric(value)

    @ItemDescriptor(float)
    def living_area(self, value):
        return self._clean_numeric(value)

    @ItemDescriptor(float)
    def external_area(self, value):
        return self._clean_numeric(value)

    @ItemDescriptor(float)
    def volume(self, value):
        return self._clean_numeric(value)

    @ItemDescriptor(str)
    def house_type(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(int)
    def construction_year(self, value):
        return self._clean_numeric(value, is_int=True)

    @ItemDescriptor(str)
    def energy_label(self, value):
        return value.strip().upper() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def balcony(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def storage(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def parking(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def status(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def insulation(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def heating(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def hot_water(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def description(self, value):
        return " ".join(value.split()) if isinstance(value, str) else value

    @ItemDescriptor(str)
    def listed_since(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def date_of_rental(self, value):
        return value.strip() if isinstance(value, str) else value

    @ItemDescriptor(str)
    def term(self, value):
        return value.strip() if isinstance(value, str) else value

    def to_dict_items(self) -> Dict:
        """Convert HouseDetail instance to a dictionary with cleaned values."""
        descriptor_names = [
            name
            for name, attr in vars(self.__class__).items()
            if isinstance(attr, ItemDescriptor)
        ]
        return {name: getattr(self, name) for name in descriptor_names}

from typing import Dict


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


class HouseDetails:
    @ItemDescriptor(int)
    def id(self, value):
        if not value:
            return 999999
        else:
            return value

    @ItemDescriptor(float)
    def price(self, value):
        """Convert price string to float, handling thousands separators"""
        if not value:
            return 0
        try:
            # Remove currency and text, handle thousands separator
            cleaned = value.replace("€", "").replace(".", "").replace(",", "")
            cleaned = cleaned.split("/")[0].split("p")[0].strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0

    def deposit(self, value):
        """Clean deposit amount, handling thousands separators"""
        if not value:
            return 0
        try:
            # Remove currency and text, handle thousands separator
            cleaned = value.replace("€", "").replace(".", "").replace(",", "")
            cleaned = cleaned.split("one-off")[0].strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0

    @ItemDescriptor(float)
    def living_area(self, value):
        """Convert area to float, handling None values"""
        if not value:
            return 0
        try:
            return float(value.replace("m²", "").strip())
        except (ValueError, AttributeError):
            return 0

    @ItemDescriptor(float)
    def external_area(self, value):
        """Convert external area to float, handling None values"""
        if not value:
            return 0
        try:
            return float(value.replace("m²", "").strip())
        except (ValueError, AttributeError):
            return 0

    @ItemDescriptor(float)
    def volume(self, value):
        """Convert volume to float, handling None values"""
        if not value:
            return 0
        try:
            return float(value.replace("m³", "").strip())
        except (ValueError, AttributeError):
            return 0

    # Property characteristics
    @ItemDescriptor(str)
    def house_type(self, value):
        """Clean property type description"""
        return value.strip()

    # Building information
    @ItemDescriptor(int)
    def construction_year(self, value):
        """Extract and clean construction year"""
        try:
            return int(value.strip())
        except ValueError:
            return 0

    @ItemDescriptor(str)
    def energy_label(self, value):
        """Clean energy label"""
        # Handle formats like "A+++", "B", etc.
        return value.strip().upper()

    # Exterior features
    @ItemDescriptor(str)
    def balcony(self, value):
        """Clean balcony information"""
        return value.strip()

    @ItemDescriptor(str)
    def storage(self, value):
        """Clean storage information"""
        return value.strip()

    @ItemDescriptor(str)
    def parking(self, value):
        """Clean parking information"""
        return value.strip()

    # Status information
    @ItemDescriptor(str)
    def status(self, value):
        """Clean property status"""
        return value.strip()

    @ItemDescriptor(list)
    def insulation(self, value):
        if not value:
            return []

        features = [
            item.strip()
            for item in value.replace(" and ", ",").split(",")
            if item.strip()
        ]
        return features

    @ItemDescriptor(list)
    def heating(self, value):
        if not value:
            return []

        features = [
            item.strip()
            for item in value.replace(" and ", ",").split(",")
            if item.strip()
        ]
        return features

    @ItemDescriptor(str)
    def hot_water(self, value):
        if not value or value.strip() == "":
            return "Not specified"
        return value.strip()

    @ItemDescriptor(str)
    def description(self, value):
        return " ".join(value.split())

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, f"_{key}", value)

    @classmethod
    def to_dict(cls):
        return {
            name: name
            for name in cls.__dict__
            if not name.startswith("_")
            and isinstance(getattr(cls, name), ItemDescriptor)
        }

    def to_dict_items(self) -> Dict:
        """Convert HouseDetails instance to a dictionary with values.

        Returns:
            Dict: A dictionary containing all descriptor field values, with field names as keys.
            For example: {'price': 1500.0, 'deposit': 2000.0, ...}
        """
        descriptor_names = [
            name
            for name, attr in vars(self.__class__).items()
            if isinstance(attr, ItemDescriptor)
        ]

        # Create dictionary with actual values from instance
        return {name: getattr(self, name) for name in descriptor_names}


class HouseInfo:

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

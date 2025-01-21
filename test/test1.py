import unittest

from model.funda import RentInfo, RentItemDescriptor


class TestRentItemDescriptor(unittest.TestCase):
    def test_basic_type_conversion(self):
        """测试基本类型转换功能"""
        rent_info = RentInfo(
            monthly_rent="€ 3,250 /maand",
            living_area="118 m²",
            bedroom_count="3",
            energy_level="C",
        )

        self.assertEqual(rent_info.monthly_rent, 3250.0)
        self.assertEqual(rent_info.living_area, 118)
        self.assertEqual(rent_info.bedroom_count, 3)
        self.assertEqual(rent_info.energy_level, "C")

    def test_none_values(self):
        """测试空值处理"""
        rent_info = RentInfo(
            monthly_rent=None, living_area=None, bedroom_count=None, energy_level=None
        )

        self.assertEqual(rent_info.monthly_rent, 0.0)
        self.assertEqual(rent_info.living_area, 0)
        self.assertEqual(rent_info.bedroom_count, 0)
        self.assertEqual(rent_info.energy_level, "")

    def test_invalid_values(self):
        """测试无效值处理"""
        rent_info = RentInfo(
            monthly_rent="invalid",
            living_area="invalid",
            bedroom_count="invalid",
            energy_level="X",  # 无效的能源等级
        )

        self.assertEqual(rent_info.monthly_rent, 0.0)
        self.assertEqual(rent_info.living_area, 0)
        self.assertEqual(rent_info.bedroom_count, 0)
        self.assertEqual(rent_info.energy_level, "")

    def test_to_dict(self):
        """测试to_dict方法"""
        data = {
            "monthly_rent": "€ 3,250 /maand",
            "living_area": "118 m²",
            "bedroom_count": "3",
            "energy_level": "C",
            "street_adress": "Test Street",
            "postal_code": "1234AB",
            "city": "Amsterdam",
            "property_agent": "Test Agent",
        }
        rent_info = RentInfo(**data)
        dict_result = rent_info.to_dict()

        self.assertEqual(dict_result["monthly_rent"], 3250.0)
        self.assertEqual(dict_result["living_area"], 118)
        self.assertEqual(dict_result["bedroom_count"], 3)
        self.assertEqual(dict_result["energy_level"], "C")
        self.assertEqual(dict_result["street_adress"], "Test Street")
        self.assertEqual(dict_result["postal_code"], "1234AB")
        self.assertEqual(dict_result["city"], "Amsterdam")
        self.assertEqual(dict_result["property_agent"], "Test Agent")

    def test_custom_pipeline(self):
        """测试自定义pipeline功能"""

        class TestClass:
            @RentItemDescriptor(float)
            def test_field(self, value):
                return value * 2 if isinstance(value, (int, float)) else 0

        test_obj = TestClass()
        test_obj.__dict__["_test_field"] = 5

        self.assertEqual(test_obj.test_field, 10.0)


if __name__ == "__main__":
    unittest.main()

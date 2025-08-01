import asyncio
import csv
import json
import os
import pathlib
from typing import Dict

import aiofiles

import config
from tools import utils
from base.base import AbstractStore
from .funda_postgre import (
    get_db,
    add_new_detail,
    add_new_listing,
    query_detail_by_id,
    query_listing_by_id,
    update_detail_by_id,
    update_listing_by_id,
)


def calculate_number_of_files(file_store_path: str) -> int:
    """Calculate the sorting number for file names"""
    # check if directory exists
    if not os.path.exists(file_store_path):
        return 1

    try:
        file_numbers = [
            int(file_name.split("_")[0]) for file_name in os.listdir(file_store_path)
        ]
        return max(file_numbers) + 1 if file_numbers else 1
    except (ValueError, IndexError):
        return 1


class FundaCsvStore(AbstractStore):
    def __init__(self, offering_type: str, search_areas: list[str]):
        self.date_folder = pathlib.Path(f"data/{utils.get_current_date()}")
        self.date_folder.mkdir(parents=True, exist_ok=True)

        area_str = "_".join(search_areas).lower()
        self.listing_file = (
            self.date_folder / f"{offering_type}_{area_str}_listings.csv"
        )
        self.detail_file = self.date_folder / f"{offering_type}_{area_str}_details.csv"

    async def _save_to_csv(self, file_path: pathlib.Path, item: Dict):
        async with aiofiles.open(
            file_path, mode="a+", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.writer(f)
            if await f.tell() == 0:
                await writer.writerow(item.keys())
            await writer.writerow(item.values())

    async def store_listing(self, content: Dict):
        await self._save_to_csv(self.listing_file, content)

    async def store_details(self, content: Dict):
        await self._save_to_csv(self.detail_file, content)


class FundaPgStore(AbstractStore):
    def __init__(self):
        self.db = get_db()

    async def store_listing(self, content: Dict):
        try:
            # Check if property already exists
            property_id = content.get("id")
            existing_listing = await query_listing_by_id(property_id)

            if not existing_listing:

                await add_new_listing(content)
            else:
                await update_listing_by_id(property_id, content)
        except Exception as e:
            raise

    async def store_details(self, content: Dict):
        try:

            # Get the property ID from the content
            property_id = content.get("property_id")
            existing_detail = await query_detail_by_id(property_id)

            if not existing_detail:

                await add_new_detail(content)
            else:

                await update_detail_by_id(property_id, content)

        except Exception as e:
            raise

    async def store_image(self, content: Dict):
        try:
            await add_new_image(content)
        except Exception as e:
            raise


class StoreFactory:
    STORES = {
        "csv": FundaCsvStore,
    }

    @staticmethod
    def create_store(method: str, **kwargs) -> AbstractStore:
        store_class = StoreFactory.STORES.get(method)
        if not store_class:
            raise ValueError(
                f"Invalid store method: {method}. Supported methods are: {list(StoreFactory.STORES.keys())}"
            )
        return store_class(**kwargs)

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
    upsert_listing,
    add_new_image,
    get_listings_for_update,
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

        # Initialize header-written flags based on file existence
        self._listing_header_written = self.listing_file.exists()
        self._detail_header_written = self.detail_file.exists()
        self._lock = asyncio.Lock()

    async def _save_to_csv(self, file_path: pathlib.Path, item: Dict, file_type: str):
        header_written_flag = f"_{file_type}_header_written"

        async with self._lock:
            # Check the flag inside the lock to ensure atomicity
            write_header = not getattr(self, header_written_flag)

            async with aiofiles.open(
                file_path, mode="a+", encoding="utf-8-sig", newline=""
            ) as f:
                writer = csv.writer(f)
                if write_header:
                    await writer.writerow(item.keys())
                    setattr(self, header_written_flag, True)
                await writer.writerow(item.values())

    async def store_listing(self, content: Dict):
        await self._save_to_csv(self.listing_file, content, "listing")

    async def store_details(self, content: Dict):
        await self._save_to_csv(self.detail_file, content, "detail")


class FundaPgStore(AbstractStore):
    def __init__(self, offering_type: str, **kwargs):
        self.db = get_db()
        self.offering_type = offering_type
        self.update_limit = kwargs.get("update_limit", 100)  # Default limit for updates

    async def get_available_listings(self) -> list[dict]:
        """Retrieves a batch of listings due for an update."""
        try:
            return await get_listings_for_update(self.offering_type, self.update_limit)
        except Exception as e:
            raise

    async def store_listing(self, content: Dict):
        """Stores a listing snapshot."""
        try:
            await upsert_listing(content, self.offering_type)
        except Exception as e:
            raise

    async def store_details(self, content: Dict, listing_record_id: int):
        """
        DEPRECATED: Details are now stored as part of the listing snapshot (details_jsonb).
        This method is kept for compatibility but does nothing.
        """
        pass

    async def store_image(self, content: Dict):
        try:
            # Add offering_type to the content dict for the images table
            content_with_type = content.copy()
            content_with_type["offering_type"] = self.offering_type
            await add_new_image(content_with_type)
        except Exception as e:
            raise


class StoreFactory:
    STORES = {"csv": FundaCsvStore, "db": FundaPgStore}

    @staticmethod
    def create_store(method: str, **kwargs) -> AbstractStore:
        store_class = StoreFactory.STORES.get(method)
        if not store_class:
            raise ValueError(
                f"Invalid store method: {method}. Supported methods are: {list(StoreFactory.STORES.keys())}"
            )
        return store_class(**kwargs)

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
    csv_store_path: str = "data/funda"

    def __init__(self):
        pathlib.Path(self.csv_store_path).mkdir(parents=True, exist_ok=True)

    def get_file_name(self, store_type, offer_type):
        file_count = calculate_number_of_files(self.csv_store_path)
        return f"{self.csv_store_path}/{file_count}_{store_type}_{offer_type}_{utils.get_current_date()}.csv"

    async def save_data_to_csv(self, save_item: Dict, store_type: str, offer_type: str):

        pathlib.Path(self.csv_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.get_file_name(
            store_type=store_type, offer_type=offer_type
        )
        async with aiofiles.open(
            save_file_name, mode="a+", encoding="utf-8-sig", newline=""
        ) as f:
            f.fileno()
            writer = csv.writer(f)
            if await f.tell() == 0:
                await writer.writerow(save_item.keys())
            await writer.writerow(save_item.values())

    async def store_details(self, content: Dict):
        await self.save_data_to_csv(
            save_item=content, store_type="detail", offer_type=config.OFFERING_TYPE
        )

    async def store_listing(self, content: Dict):
        await self.save_data_to_csv(
            save_item=content, store_type="listing", offer_type=config.OFFERING_TYPE
        )


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


class StoreFactory:
    STORES = {
        "csv": FundaCsvStore,
    }

    @staticmethod
    def create_store(method: str) -> AbstractStore:
        crawler_class = StoreFactory.STORES.get(method)
        if not crawler_class:
            raise ValueError(
                "Invalid Media Platform Currently only supported funda, and ..."
            )
        return crawler_class()

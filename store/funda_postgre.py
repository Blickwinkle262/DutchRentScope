from typing import Dict, Optional
import asyncpg

from db import PropertyDB


def get_db() -> PropertyDB:
    if PropertyDB._instance is None:
        raise RuntimeError(
            "Database not initialized. Call PropertyDB.initialize() first"
        )
    return PropertyDB._instance


async def query_listing_by_id(property_id: int) -> Dict:
    """
    Query property listing by property ID

    Args:
        property_id: Property identifier
    Returns:
        Dictionary containing property listing data or empty dict if not found
    """
    db = get_db()
    sql = "SELECT * FROM property_listings WHERE id = $1"
    rows = await db.query(sql, property_id)
    return rows[0] if rows else dict()


async def add_new_listing(listing_item: Dict) -> int:
    db = get_db()
    columns = list(listing_item.keys())
    placeholders = [f"${i+1}" for i in range(len(columns))]
    values = list(listing_item.values())

    sql = f"""
        INSERT INTO property_listings ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING id
    """

    result = await db.query(sql, *values)
    return result[0]["id"] if result else 0


async def update_listing_by_id(property_id: int, listing_item: Dict) -> int:
    db = get_db()
    set_items = [f"{k} = ${i+2}" for i, k in enumerate(listing_item.keys())]
    values = list(listing_item.values())

    sql = f"""
        UPDATE property_listings
        SET {', '.join(set_items)}
        WHERE id = $1
    """

    result = await db.execute(sql, property_id, *values)
    return int(result.split()[-1])


# Similar functions for property details
async def query_detail_by_id(property_id: int) -> Dict:
    db = get_db()
    sql = "SELECT * FROM property_details WHERE property_id = $1"
    rows = await db.query(sql, property_id)
    return rows[0] if rows else dict()


async def add_new_detail(detail_item: Dict) -> int:
    db = get_db()
    columns = list(detail_item.keys())
    placeholders = [f"${i+1}" for i in range(len(columns))]
    values = list(detail_item.values())

    sql = f"""
        INSERT INTO property_details ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING property_id
    """

    result = await db.query(sql, *values)
    return result[0]["property_id"] if result else 0


async def update_detail_by_id(property_id: int, detail_item: Dict) -> int:
    db = get_db()
    set_items = [f"{k} = ${i+2}" for i, k in enumerate(detail_item.keys())]
    values = list(detail_item.values())

    sql = f"""
        UPDATE property_details
        SET {', '.join(set_items)}
        WHERE property_id = $1
    """

    result = await db.execute(sql, property_id, *values)
    return int(result.split()[-1])

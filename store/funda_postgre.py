import json
import hashlib
import zlib
import base64
from typing import Dict, List, Any

from db import PropertyDB

# --- Constants for field separation ---

# Fields that are considered static and belong to the main listings table.
# Based on the flattened structure of Property/BuyProperty in m_response.py
LISTING_STATIC_FIELDS = {
    "address_country",
    "address_province",
    "address_city",
    "address_municipality",
    "address_district",
    "address_neighbourhood",
    "address_street",
    "address_number",
    "address_suffix",
    "address_postal_code",
    "address_is_bag",
    "latitude",
    "longitude",
    # --- Promoted fields for better query performance ---
    "property_type",
    "construction_year",
    "living_area",
    "plot_area",
    "number_of_rooms",
    "number_of_bedrooms",
    "energy_label",
}

# Fields that are considered volatile and will be stored in snapshots.
# This includes all fields from m_house_detail.py and the non-static fields from m_response.py
LISTING_VOLATILE_FIELDS = {
    # From m_response.py
    "type",
    "status",
    "zoning",
    "construction_type",
    "floor_area",  # Kept here for JSONB, but living_area is the primary static field
    "plot_area",  # Kept here for JSONB, but plot_area is the primary static field
    "floor_area_range_min",
    "floor_area_range_max",
    "plot_area_range_min",
    "plot_area_range_max",
    "rent_price",
    "rent_price_condition",
    "rent_price_type",
    "rent_price_range_min",
    "rent_price_range_max",
    "asking_price",
    "asking_price_range_min",
    "asking_price_range_max",
    "price_type",
    "agent_name",
    "detail_url",
    "media_types",
    "publish_date",
    "blikvanger_enabled",
    "crawl_date",
    # From m_house_detail.py
    "price",
    "deposit",
    "external_area",
    "volume",
    "house_type",
    "balcony",
    "storage",
    "parking",
    "insulation",
    "heating",
    "hot_water",
    "description",
    "listed_since",
    "date_of_rental",
    "term",
}


def get_db() -> PropertyDB:
    """Retrieves the singleton database instance."""
    if PropertyDB._instance is None:
        raise RuntimeError(
            "Database not initialized. Call PropertyDB.initialize() first"
        )
    return PropertyDB._instance


def _calculate_row_hash(data: Dict[str, Any]) -> str:
    """Calculates a SHA-256 hash for a dictionary's volatile fields."""
    # Ensure consistent ordering and format for hashing
    serialized_data = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized_data.encode("utf-8")).hexdigest()


async def upsert_listing(listing_item: Dict, offering_type: str) -> None:
    """
    Inserts or updates a listing using the SCD-Type-2 and idempotent write approach.
    """
    db = get_db()
    listing_table = f"{offering_type}_listings"
    snapshot_table = f"{offering_type}_listing_snapshots"

    # Rename 'id' to 'listing_id' for consistency
    if "id" in listing_item:
        listing_item["listing_id"] = listing_item.pop("id")

    listing_id = listing_item.get("listing_id")
    if not listing_id:
        raise ValueError("listing_id is missing from the data.")

    # Separate static, volatile, and detail fields
    static_data = {k: v for k, v in listing_item.items() if k in LISTING_STATIC_FIELDS}
    volatile_data = {
        k: v for k, v in listing_item.items() if k in LISTING_VOLATILE_FIELDS
    }

    # Consolidate price fields from either rent or buy
    price = volatile_data.pop("rent_price", None)
    if price is None:
        price = volatile_data.pop("asking_price", None)

    if price is not None:
        volatile_data["price"] = price

    # The rest of the data goes into the JSONB column
    details_jsonb = {
        k: v for k, v in volatile_data.items() if k not in ["status", "price"]
    }

    # Compress description if it exists
    if "description" in details_jsonb and details_jsonb["description"]:
        description_str = details_jsonb["description"]
        # 1. Encode to bytes
        description_bytes = description_str.encode("utf-8")
        # 2. Compress
        compressed_bytes = zlib.compress(description_bytes)
        # 3. Base64 encode
        base64_bytes = base64.b64encode(compressed_bytes)
        # 4. Decode to string for JSON serialization
        details_jsonb["description"] = base64_bytes.decode("ascii")
        # Add a flag to indicate compression
        details_jsonb["description_is_compressed"] = True

    core_volatile_data = {
        "status": volatile_data.get("status"),
        "price": volatile_data.get("price"),
        "details_jsonb": json.dumps(details_jsonb),  # Store as JSON string
    }

    row_hash = _calculate_row_hash(core_volatile_data)

    async with db.pool.acquire() as connection:
        async with connection.transaction():
            # Step 1: Get the latest hash for the listing, if it exists
            latest_hash_result = await connection.fetchrow(
                f"""
                SELECT row_hash FROM {snapshot_table}
                WHERE listing_id = $1
                ORDER BY snapshot_ts DESC
                LIMIT 1
                """,
                listing_id,
            )
            latest_hash = latest_hash_result["row_hash"] if latest_hash_result else None

            # Step 2: If hash is different, we need to write a new snapshot
            if row_hash != latest_hash:
                # Step 2a: Ensure the main listing record exists (UPSERT)
                if static_data:
                    # If there is static data, include it in the insert
                    columns = ", ".join(static_data.keys())
                    placeholders = ", ".join(f"${i+2}" for i in range(len(static_data)))
                    sql = f"""
                        INSERT INTO {listing_table} (listing_id, {columns})
                        VALUES ($1, {placeholders})
                        ON CONFLICT (listing_id) DO UPDATE SET
                        last_seen_at = NOW()
                    """
                    await connection.execute(sql, listing_id, *static_data.values())
                else:
                    # If there is no static data, just insert the ID
                    sql = f"""
                        INSERT INTO {listing_table} (listing_id)
                        VALUES ($1)
                        ON CONFLICT (listing_id) DO UPDATE SET
                        last_seen_at = NOW()
                    """
                    await connection.execute(sql, listing_id)

                # Step 2b: Insert the new snapshot
                new_snapshot = await connection.fetchrow(
                    f"""
                    INSERT INTO {snapshot_table} (listing_id, row_hash, status, price, details_jsonb)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING snapshot_id
                    """,
                    listing_id,
                    row_hash,
                    core_volatile_data["status"],
                    core_volatile_data["price"],
                    core_volatile_data["details_jsonb"],
                )
                new_snapshot_id = new_snapshot["snapshot_id"]

                # Step 2c: Update the main listing to point to the new snapshot
                await connection.execute(
                    f"""
                    UPDATE {listing_table}
                    SET current_snapshot_id = $1, last_seen_at = NOW()
                    WHERE listing_id = $2
                    """,
                    new_snapshot_id,
                    listing_id,
                )
            else:
                # Step 3: If hash is the same, just update last_seen_at
                await connection.execute(
                    f"""
                    UPDATE {listing_table} SET last_seen_at = NOW()
                    WHERE listing_id = $1
                    """,
                    listing_id,
                )


async def get_listings_for_update(offering_type: str, limit: int) -> List[Dict]:
    """
    Atomically retrieves and removes a batch of listings due for an update.
    """
    db = get_db()
    active_table = f"active_{offering_type}_listings"

    sql = f"""
        WITH due_listings AS (
            SELECT listing_id
            FROM {active_table}
            WHERE next_update_ts <= NOW()
            LIMIT {limit}
            FOR UPDATE SKIP LOCKED
        )
        DELETE FROM {active_table} a
        USING due_listings dl
        WHERE a.listing_id = dl.listing_id
        RETURNING a.listing_id;
    """
    # In a real-world scenario, you'd also join with the main listings table
    # to return more data like `detail_url`, but for now, this is sufficient.
    result = await db.query(sql)
    return result if result else []


async def add_new_image(image_item: Dict) -> int:
    """
    Adds a new image's metadata to the house_images table.
    """
    db = get_db()
    # Ensure required keys are present
    required_keys = {"listing_id", "offering_type", "image_url"}
    if not required_keys.issubset(image_item.keys()):
        raise ValueError(f"Missing one of the required keys: {required_keys}")

    columns = list(image_item.keys())
    placeholders = [f"${i+1}" for i in range(len(columns))]
    values = list(image_item.values())

    sql = f"""
        INSERT INTO house_images ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        ON CONFLICT (image_url) DO NOTHING
        RETURNING id
    """

    result = await db.query(sql, *values)
    return result[0]["id"] if result else 0

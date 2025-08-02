from typing import Dict, Optional
import asyncpg
import logging

from config import POSTGRES_DSN

logger = logging.getLogger("root")


class PropertyDB:
    """Database connection handler for property data"""

    _instance = None  # Singleton instance

    def __init__(self):
        self.pool = None

    @classmethod
    async def initialize(cls):
        """Initialize the database connection with proper logging"""
        if cls._instance is None:
            cls._instance = cls()

        try:
            logger.info("Initializing PostgreSQL connection pool")
            cls._instance.pool = await asyncpg.create_pool(
                POSTGRES_DSN, min_size=5, max_size=20
            )
            logger.info("PostgreSQL connection pool initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database connection: %s", str(e))
            raise

    async def query(self, *args, **kwargs):
        if not self.pool:
            raise RuntimeError("Database pool is not initialized.")
        return await self.pool.fetch(*args, **kwargs)

    async def execute(self, *args, **kwargs):
        if not self.pool:
            raise RuntimeError("Database pool is not initialized.")
        return await self.pool.execute(*args, **kwargs)

    async def close(self):
        if self.pool:
            try:
                logger.info("Closing PostgreSQL connection pool")
                await self.pool.close()
                self.pool = None
                logger.info("PostgreSQL connection pool closed successfully")
            except Exception as e:
                logger.error("Error closing database connection: %s", str(e))
                raise


async def init_db():
    logger.info("Starting database initialization")
    try:
        await PropertyDB.initialize()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error("Database initialization failed %s", str(e))
        raise


async def close_db():

    logger.info("Starting database cleanup")
    try:
        await PropertyDB._instance.close()
        logger.info("Database cleanup completed successfully")
    except Exception as e:
        logger.error("Database cleanup failed %s", str(e))
        raise


async def manage_active_listings(offering_type: str, update_interval_days: int = 7):
    """
    Manages the active listings queue for a given offering type.
    - Adds newly available listings to the queue.
    - Removes sold/rented/inactive listings from the queue.
    """
    db = PropertyDB._instance
    if not db or not db.pool:
        raise RuntimeError("Database is not initialized.")

    listing_table = f"{offering_type}_listings"
    snapshot_table = f"{offering_type}_listing_snapshots"
    active_table = f"active_{offering_type}_listings"

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            # Add new active listings
            add_sql = f"""
                INSERT INTO {active_table} (listing_id, next_update_ts)
                SELECT l.listing_id, NOW() + INTERVAL '{update_interval_days} days'
                FROM {listing_table} l
                JOIN {snapshot_table} s ON l.current_snapshot_id = s.snapshot_id
                WHERE (s.status ILIKE '%available%' OR s.status ILIKE '%beschikbaar%')
                  AND l.listing_id NOT IN (SELECT listing_id FROM {active_table})
            """
            added_result = await conn.execute(add_sql)
            logger.info(
                f"[{offering_type}] Added {added_result.split(' ')[-1]} new listings to the active queue."
            )

            # Remove inactive listings
            remove_sql = f"""
                DELETE FROM {active_table}
                WHERE listing_id IN (
                    SELECT l.listing_id
                    FROM {listing_table} l
                    JOIN {snapshot_table} s ON l.current_snapshot_id = s.snapshot_id
                    WHERE s.status IS NOT NULL 
                      AND s.status NOT ILIKE '%available%' 
                      AND s.status NOT ILIKE '%beschikbaar%'
                )
            """
            removed_result = await conn.execute(remove_sql)
            logger.info(
                f"[{offering_type}] Removed {removed_result.split(' ')[-1]} inactive listings from the active queue."
            )

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

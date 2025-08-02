import asyncio
import sys
import logging

import cmd_arg
import config
import db

from base.base import AbstractCrawler
from platforms.funda.core import FundaCrawler

from tools.utils import setup_logging

setup_logging()

logger = logging.getLogger("root")


class CrawlerFactory:
    CRAWLERS = {
        "funda": FundaCrawler,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError(
                "Invalid Media Platform Currently only supported funda, and ..."
            )
        return crawler_class()


async def main():
    # parse cmd
    await cmd_arg.parse_cmd()

    # init db
    if config.SAVE_DATA_OPTION == "db":
        logger.info("Connecting to the database...")
        await db.init_db()
        logger.info("Database connection established.")
        logger.warning("Automatic database schema setup has been removed.")
        logger.warning(
            "Please run `python -m tools.db_manager --execute-sql [your_schema.sql]` manually if tables are missing."
        )

    # If --run-etl is specified, run the ETL process and exit
    if config.RUN_ETL:
        if config.SAVE_DATA_OPTION != "db":
            logger.error("--run-etl requires --save_option 'db'")
            return

        logger.info("Starting ETL process to manage active listings...")
        await db.init_db()  # Ensure DB is connected
        await db.manage_active_listings(offering_type=config.OFFERING_TYPE)
        await db.close_db()  # Close connection after ETL
        logger.info("ETL process finished.")

    else:
        # Otherwise, run the crawler as usual
        crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
        await crawler.start()

        # After a crawl that modifies data, automatically update the active listings queue
        if config.SAVE_DATA_OPTION == "db" and config.FUNDA_CRAWL_TYPE in [
            "detail",
            "update",
        ]:
            logger.info(
                "Crawl finished. Automatically updating the active listings queue..."
            )
            await db.init_db()  # Ensure DB is connected
            await db.manage_active_listings(offering_type=config.OFFERING_TYPE)
            await db.close_db()  # Close connection after update
            logger.info("Active listings queue updated.")

    # Final check to close DB if it was opened but not closed by the ETL/update logic
    if (
        config.SAVE_DATA_OPTION == "db"
        and db.PropertyDB._instance
        and db.PropertyDB._instance.pool
    ):
        logger.info("Closing main database connection.")
        await db.close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
        # asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()

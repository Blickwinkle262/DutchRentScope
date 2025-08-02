import argparse
import asyncio
import asyncpg
import logging
from pathlib import Path

# This is a workaround to import config when running as a script
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import POSTGRES_DSN
from tools.utils import setup_logging

logger = logging.getLogger("root")


async def execute_sql_file(file_path: Path):
    """
    Reads an SQL file and executes its content against the database.
    """
    if not POSTGRES_DSN:
        logger.error("POSTGRES_DSN is not configured. Cannot execute SQL file.")
        return

    if not file_path.exists():
        logger.error(f"Schema file not found at {file_path}")
        return

    try:
        sql_content = file_path.read_text()
        # Use a connection from a pool if available, otherwise create a new one
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
        logger.info(f"Executing SQL from {file_path}...")
        await conn.execute(sql_content)
        await conn.close()
        logger.info(f"Successfully executed SQL from {file_path}.")
    except Exception as e:
        logger.error(f"Failed to execute SQL file {file_path}: {e}", exc_info=True)
        raise


async def main():
    """
    Main function to handle command-line arguments for the DB manager.
    """
    setup_logging()
    parser = argparse.ArgumentParser(description="Database Management Tool")
    parser.add_argument(
        "--execute-sql",
        type=Path,
        help="Path to the SQL file to execute.",
        metavar="FILE_PATH",
    )
    args = parser.parse_args()

    if args.execute_sql:
        await execute_sql_file(args.execute_sql)
    else:
        logger.info(
            "No action specified. Use --execute-sql FILE_PATH to run a SQL file."
        )


if __name__ == "__main__":
    asyncio.run(main())

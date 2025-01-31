import argparse

import config


async def parse_cmd():
    parser = argparse.ArgumentParser(
        description="crawler for Dutch house rent or purchase"
    )
    parser.add_argument(
        "--platform",
        type=str,
        help="house rent platform including funda, and ...",
        choices=["funda"],
        default=config.PLATFORM,
    )
    parser.add_argument(
        "--crawl_type",
        type=str,
        help="choose between listing and detail, detail will continue crawl detail page and get more info",
        choices=["detail", "listing"],
        default=config.FUNDA_CRAWL_TYPE,
    )
    parser.add_argument(
        "--search_areas",
        type=str,
        nargs="+",
        help="areas for searching like amsterdam, rotterdam",
        default=config.SEARCH_AREAS,
    )
    parser.add_argument(
        "--download_img",
        action="store_true",
        help="Enable image downloading",
        default=config.DOWNLOAD_IMAGES,
    )
    parser.add_argument(
        "--image_size",
        choices=["small", "medium", "large"],
        help="Select image size (only used if download_img is enabled)",
        default=config.IMAGE_SIZE,
    )
    parser.add_argument(
        "--min_price",
        type=float,
        default=None,
        help="Minimum price filter (optional)",
    )
    parser.add_argument(
        "--max_price", type=float, default=None, help="Maximum price filter (optional)"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="pages default to start, default start from 1st page",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="stop to crawl when reach page, default None will crawl all",
    )
    parser.add_argument(
        "--save_option",
        type=str,
        choices=["db", "csv", "json"],
        default=config.SAVE_DATA_OPTION,
    )

    def validate_price_range(args):
        if args.min_price is not None and args.max_price is not None:
            if args.min_price > args.max_price:
                parser.error("min_price cannot be greater than max_price")

    args = parser.parse_args()
    validate_price_range(args)

    # override config
    config.PLATFORM = args.platform
    config.SEARCH_AREAS = args.search_areas
    config.DOWNLOAD_IMAGES = args.download_img
    config.IMAGE_SIZE = args.image_size
    config.PRICE_MIN = args.min_price
    config.PRICE_MAX = args.max_price
    config.START_PAGE = args.start
    config.END_PAGE = args.end
    config.SAVE_DATA_OPTION = args.save_option
    config.FUNDA_CRAWL_TYPE = args.crawl_type

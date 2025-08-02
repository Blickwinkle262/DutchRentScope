import atexit
import json
import logging.config
import logging.handlers
import pathlib
import random
import time
import aiohttp
from pathlib import Path
from bs4 import BeautifulSoup

from io import BytesIO
from typing import Dict, List, Optional, Tuple, Set
from playwright.async_api import Cookie, Page

import aiofiles


def get_user_agent() -> str:
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5112.79 Safari/537.36",
    ]
    return random.choice(ua_list)


def convert_cookies(
    cookies: Optional[List[Cookie]],
) -> Tuple[str, Dict]:
    if not cookies:
        return "", {}

    cookies_str = "; ".join(
        [f"{cookie.get('name')}={cookie.get('value')}" for cookie in cookies]
    )
    cookie_dict = {cookie.get("name"): cookie.get("value") for cookie in cookies}

    return cookies_str, cookie_dict


def convert_str_cookie_to_dict(cookie_str: str) -> Dict:
    cookie_dict: Dict[str, str] = dict()
    if not cookie_str:
        return cookie_dict
    for cookie in cookie_str.split(";"):
        cookie = cookie.strip()
        if not cookie:
            continue
        cookie_list = cookie.split("=")
        if len(cookie_list) != 2:
            continue
        cookie_value = cookie_list[1]
        if isinstance(cookie_value, list):
            cookie_value = "".join(cookie_value)
        cookie_dict[cookie_list[0]] = cookie_value
    return cookie_dict


def generate_image_url(thumb_id: int, size: str = "medium") -> str:
    size_map = {"small": "360x240", "medium": "720x480", "large": "1440x960"}
    if size not in size_map:
        raise ValueError(f"Size must be one of {list(size_map.keys())}")
    thumb_id_str = str(thumb_id).zfill(9)
    parts = [thumb_id_str[:3], thumb_id_str[3:6], thumb_id_str[6:]]

    resolution = size_map[size]
    return f"https://cloud.funda.nl/valentina_media/{parts[0]}/{parts[1]}/{parts[2]}_{resolution}.jpg"


async def download_single_image(
    url: str, save_path: Path, session: aiohttp.ClientSession
) -> bool:
    try:
        async with session.get(url) as response:
            if response.status == 200:
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(await response.read())
                return True
            return False
    except Exception as e:
        logging.error(f"Error downloading {url}: {str(e)}")
        return False


funda_headers = {
    "Host": "listing-search-wonen.funda.io",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Accept": "application/x-ndjson",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.funda.nl/",
    "content-type": "application/x-ndjson",
    "Origin": "https://www.funda.nl",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "Sec-GPC": "1",
    "Priority": "u=4",
    "TE": "trailers",
}


def get_current_date() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def setup_logging():
    log_dir = pathlib.Path("logs")
    log_dir.mkdir(exist_ok=True)
    config_file = pathlib.Path("config/log_config.json")
    with open(config_file) as f_in:
        config = json.load(f_in)
    config["handlers"]["file"]["filename"] = str(log_dir / "crawler.log")
    logging.config.dictConfig(config)
    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


async def save_error_html(city: str, house_id: str, html_content: str):
    """Saves the HTML content of a failed page to a structured directory."""
    date_str = get_current_date()
    error_dir = Path(f"data/error_html/{date_str}/{city}")
    error_dir.mkdir(parents=True, exist_ok=True)
    file_path = error_dir / f"{house_id}.html"
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(html_content)


def clean_html_content(html_content: str) -> str:
    """
    Cleans the HTML content by removing script and style tags and returning only the body.
    """
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        body = soup.find("body")
        if body:
            return str(body)
        return str(soup)
    except Exception as e:
        logging.error(f"Error cleaning HTML: {e}")
        return html_content

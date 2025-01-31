HEADLESS = False

SEARCH_DATE = "20241206"  # default param for integrate to funda search param move to default variable later

PLATFORM = "funda"

FUNDA_CRAWL_TYPE = (
    "detail"  # support listing | detail listing will not fetch detail page
)

DOWNLOAD_IMAGES = False

IMAGE_SIZE = "medium"  # support "small" | "medium" and "large"

SEARCH_AREAS = ["leiden", "amsterdam"]

OFFERING_TYPE = "rent"

PRICE_MIN = 0
PRICE_MAX = 3000

START_PAGE = 1
END_PAGE = 3

MAX_CONCURRENCY_NUM = 5

SAVE_DATA_OPTION = "csv"  # support "db" and "csv"

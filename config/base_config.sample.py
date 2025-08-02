HEADLESS = False

SEARCH_DATE = "20241206"  # default param for integrate to funda search param move to default variable later

PLATFORM = "funda"

FUNDA_CRAWL_TYPE = (
    "detail"  # support listing | detail listing will not fetch detail page
)


DOWNLOAD_IMAGES = False

IMAGE_SIZE = "medium"  # support "small" | "medium" and "large"

SEARCH_AREAS = ["leiden"]

OFFERING_TYPE = "rent"  # "rent" or "buy"

# Filters, default to None if not provided via command line
AVAILABILITY = None
CONSTRUCTION_PERIOD = None

PRICE_MIN = 0
PRICE_MAX = 3000

START_PAGE = 1
END_PAGE = 3

MAX_CONCURRENCY_NUM = 5

# Batch size for processing house details
BATCH_SIZE = 50

# Cookie Management
MAX_COOKIE_FAILURE_COUNT = 3  # Max failures before forcing a new cookie
MAX_COOKIE_UPDATE_LIMIT = 5  # Max total cookie updates before halting

# Throttling
RANDOM_DELAY_MIN = 1  # Minimum random delay in seconds
RANDOM_DELAY_MAX = 5  # Maximum random delay in seconds

SAVE_DATA_OPTION = "csv"  # support "db" and "csv"

POSTGRES_DSN = "postgresql://user:password@host:port/database"

UPDATE_SINCE_DAYS = 7

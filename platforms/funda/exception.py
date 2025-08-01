from httpx import RequestError


class DataFetchError(RequestError):
    """Data acquiring error during fetching"""


class IPBlockError(RequestError):
    """IP block"""


class PaginationLimitError(Exception):
    """Raised when pagination exceeds the search engine's max_result_window limit"""

    def __init__(
        self,
        message="Pagination limit exceeded. Try reducing the page range or using more specific search criteria.",
        max_limit=10000,
    ):
        self.max_limit = max_limit
        super().__init__(message)


class EmptyResponseError(Exception):
    """Raised when API returns an empty or invalid response structure"""

    def __init__(self, message="API returned empty or invalid response structure"):
        super().__init__(message)

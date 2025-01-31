from httpx import RequestError


class DataFetchError(RequestError):
    """Data acquiring error during fetching"""


class IPBlockError(RequestError):
    """IP block"""

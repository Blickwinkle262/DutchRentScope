from abc import ABC, abstractmethod
from typing import Optional


class AbstractCookieManager(ABC):
    """
    Abstract base class for cookie managers.
    Defines the interface for getting, loading, saving, and fetching cookies.
    """

    @abstractmethod
    async def get_cookie(self, force_refresh: bool = False) -> str:
        """
        Get a valid cookie string.

        Args:
            force_refresh: If True, forces fetching a new cookie, ignoring any cached version.

        Returns:
            A valid cookie string.
        """
        pass

    @abstractmethod
    def _load_cookie(self) -> Optional[dict]:
        """
        Load cookie data from a local file.

        Returns:
            A dictionary containing cookie data or None if not found or invalid.
        """
        pass

    @abstractmethod
    def _save_cookie(self, cookie_data: dict):
        """
        Save cookie data to a local file.

        Args:
            cookie_data: A dictionary containing the cookie string and its metadata.
        """
        pass

    @abstractmethod
    async def _fetch_new_cookie(self) -> str:
        """
        Fetch a new cookie string by launching a browser.

        Returns:
            A new, valid cookie string.
        """
        pass

    @abstractmethod
    def _is_cookie_valid(self) -> bool:
        """
        Check if the currently loaded cookie is still valid.

        Returns:
            True if the cookie is valid, False otherwise.
        """
        pass

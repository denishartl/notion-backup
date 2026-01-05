# ABOUTME: Wrapper around the official Notion Python SDK.
# ABOUTME: Provides authenticated client and discovery of all accessible content.

import functools
import logging
import time
from dataclasses import dataclass

from notion_client import Client
from notion_client.errors import APIResponseError
from notion_client.helpers import collect_paginated_api

from ..concurrency import RateLimiter

logger = logging.getLogger(__name__)


def retry_on_rate_limit(max_retries: int = 3):
    """Decorator to retry on 429 responses using Retry-After header.

    Args:
        max_retries: Maximum number of retry attempts.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except APIResponseError as e:
                    if e.status == 429 and attempt < max_retries - 1:
                        retry_after = 1
                        if hasattr(e, "headers") and e.headers:
                            retry_after = int(e.headers.get("Retry-After", 1))
                        logger.warning(
                            f"Rate limited, retrying in {retry_after}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_after)
                        continue
                    raise
            return None  # Unreachable but satisfies type checker
        return wrapper
    return decorator


@dataclass
class WorkspaceContent:
    """All pages and databases accessible to the integration."""
    pages: list[dict]
    databases: list[dict]


class NotionClient:
    """Wrapper around the Notion SDK client."""

    def __init__(self, token: str):
        self._client = Client(auth=token)

    def discover_content(self) -> WorkspaceContent:
        """Discover all pages and databases shared with this integration.

        Uses the search API with pagination to find all accessible content.
        """
        logger.info("Discovering workspace content...")

        pages = []
        databases = []

        cursor = None
        while True:
            response = self._client.search(
                start_cursor=cursor,
                page_size=100,
            )

            for item in response["results"]:
                if item["object"] == "page":
                    pages.append(item)
                elif item["object"] == "database":
                    databases.append(item)

            if not response["has_more"]:
                break
            cursor = response["next_cursor"]

        logger.info(f"Found {len(pages)} pages and {len(databases)} databases")
        return WorkspaceContent(pages=pages, databases=databases)

    def get_page(self, page_id: str) -> dict:
        """Retrieve a page by ID."""
        return self._client.pages.retrieve(page_id=page_id)

    def get_blocks(self, block_id: str) -> list[dict]:
        """Retrieve all child blocks of a block/page."""
        return collect_paginated_api(
            self._client.blocks.children.list,
            block_id=block_id,
        )

    def get_database(self, database_id: str) -> dict:
        """Retrieve database schema by ID."""
        return self._client.databases.retrieve(database_id=database_id)

    def query_database(self, database_id: str) -> list[dict]:
        """Query all rows from a database."""
        return collect_paginated_api(
            self._client.databases.query,
            database_id=database_id,
        )


class RateLimitedNotionClient(NotionClient):
    """NotionClient with rate limiting and automatic retry on 429.

    Wraps all API methods with rate limiting to stay within Notion's
    3 requests/second limit, and retries automatically if rate limited.
    """

    def __init__(self, token: str, rate_limiter: RateLimiter):
        """Initialize rate-limited client.

        Args:
            token: Notion integration token.
            rate_limiter: RateLimiter instance to throttle requests.
        """
        super().__init__(token)
        self._rate_limiter = rate_limiter

    @retry_on_rate_limit()
    def discover_content(self) -> WorkspaceContent:
        """Discover all pages and databases with rate limiting."""
        logger.info("Discovering workspace content...")

        pages = []
        databases = []

        cursor = None
        while True:
            self._rate_limiter.acquire()
            response = self._client.search(
                start_cursor=cursor,
                page_size=100,
            )

            for item in response["results"]:
                if item["object"] == "page":
                    pages.append(item)
                elif item["object"] == "database":
                    databases.append(item)

            if not response["has_more"]:
                break
            cursor = response["next_cursor"]

        logger.info(f"Found {len(pages)} pages and {len(databases)} databases")
        return WorkspaceContent(pages=pages, databases=databases)

    @retry_on_rate_limit()
    def get_page(self, page_id: str) -> dict:
        """Retrieve a page by ID with rate limiting."""
        self._rate_limiter.acquire()
        return self._client.pages.retrieve(page_id=page_id)

    @retry_on_rate_limit()
    def get_blocks(self, block_id: str) -> list[dict]:
        """Retrieve all child blocks with rate limiting."""
        self._rate_limiter.acquire()
        return collect_paginated_api(
            self._client.blocks.children.list,
            block_id=block_id,
        )

    @retry_on_rate_limit()
    def get_database(self, database_id: str) -> dict:
        """Retrieve database schema by ID with rate limiting."""
        self._rate_limiter.acquire()
        return self._client.databases.retrieve(database_id=database_id)

    @retry_on_rate_limit()
    def query_database(self, database_id: str) -> list[dict]:
        """Query all rows from a database with rate limiting."""
        self._rate_limiter.acquire()
        return collect_paginated_api(
            self._client.databases.query,
            database_id=database_id,
        )

# ABOUTME: Wrapper around the official Notion Python SDK.
# ABOUTME: Provides authenticated client and discovery of all accessible content.

import logging
from dataclasses import dataclass

from notion_client import Client
from notion_client.helpers import collect_paginated_api

logger = logging.getLogger(__name__)


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

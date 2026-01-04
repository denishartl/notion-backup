# ABOUTME: Notion API integration package.
# ABOUTME: Exports client and fetching functions for pages and databases.

from .client import NotionClient
from .pages import fetch_page_with_blocks
from .databases import fetch_database_with_rows

__all__ = ["NotionClient", "fetch_page_with_blocks", "fetch_database_with_rows"]

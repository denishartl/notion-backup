# ABOUTME: Page and block fetching logic for Notion backup.
# ABOUTME: Recursively retrieves all blocks within a page.

import logging
from dataclasses import dataclass

from .client import NotionClient

logger = logging.getLogger(__name__)

# Block types that can have children
BLOCKS_WITH_CHILDREN = {
    "paragraph",
    "bulleted_list_item",
    "numbered_list_item",
    "toggle",
    "to_do",
    "quote",
    "callout",
    "synced_block",
    "template",
    "column",
    "column_list",
    "table",
    "table_row",
}


@dataclass
class PageData:
    """Complete page data including properties and all blocks."""
    page: dict
    blocks: list[dict]


def fetch_blocks_recursive(client: NotionClient, block_id: str) -> list[dict]:
    """Fetch all blocks under a parent, recursively fetching children.

    Args:
        client: The Notion API client.
        block_id: The ID of the parent block or page.

    Returns:
        List of blocks with their children populated in-place.
    """
    blocks = client.get_blocks(block_id)

    for block in blocks:
        block_type = block.get("type")
        has_children = block.get("has_children", False)

        if has_children and block_type in BLOCKS_WITH_CHILDREN:
            children = fetch_blocks_recursive(client, block["id"])
            block["children"] = children

    return blocks


def fetch_page_with_blocks(client: NotionClient, page_id: str) -> PageData:
    """Fetch a page with all its properties and blocks.

    Args:
        client: The Notion API client.
        page_id: The ID of the page to fetch.

    Returns:
        PageData containing page properties and all blocks.
    """
    logger.debug(f"Fetching page {page_id}")

    page = client.get_page(page_id)
    blocks = fetch_blocks_recursive(client, page_id)

    return PageData(page=page, blocks=blocks)

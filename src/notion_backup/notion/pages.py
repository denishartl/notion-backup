# ABOUTME: Page and block fetching logic for Notion backup.
# ABOUTME: Recursively retrieves all blocks within a page.

import logging
from dataclasses import dataclass

from notion_client.errors import APIErrorCode, APIResponseError

from .client import NotionClient

logger = logging.getLogger(__name__)

# Errors meaning a child block is permanently inaccessible (not shared with
# the integration). These are skipped so the rest of the page is still backed up.
PERMANENT_BLOCK_ERRORS = {APIErrorCode.ObjectNotFound, APIErrorCode.RestrictedResource}

# Rows of synced databases, such as GitHub pull requests mirrored by Notion's
# GitHub integration, mirror objects owned by another tool. The API returns their
# properties but rejects any request for their child blocks with a validation
# error naming this type.
SYNCED_ROW_BLOCK_TYPE = "external_object_instance_page"

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
        List of blocks with their children populated in-place. A synced
        database row has no API-readable content and yields an empty list.
    """
    try:
        blocks = client.get_blocks(block_id)
    except APIResponseError as e:
        if e.code != APIErrorCode.ValidationError or SYNCED_ROW_BLOCK_TYPE not in str(e):
            raise
        logger.debug(f"Block {block_id} is a synced database row with no API-readable content")
        return []

    for block in blocks:
        block_type = block.get("type")
        has_children = block.get("has_children", False)

        if has_children and block_type in BLOCKS_WITH_CHILDREN:
            try:
                block["children"] = fetch_blocks_recursive(client, block["id"])
            except APIResponseError as e:
                if e.code in PERMANENT_BLOCK_ERRORS:
                    logger.warning(
                        f"Skipping inaccessible child block {block['id']}: {e}"
                    )
                else:
                    raise

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

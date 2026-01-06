# ABOUTME: Database and data source fetching logic for Notion backup.
# ABOUTME: Retrieves schema and all rows for databases and data sources.

import logging
from dataclasses import dataclass

from .client import NotionClient

logger = logging.getLogger(__name__)


@dataclass
class DatabaseData:
    """Complete database/data source data including schema and all rows."""
    database: dict
    rows: list[dict]


def fetch_database_with_rows(client: NotionClient, database_id: str) -> DatabaseData:
    """Fetch a database with its schema and all rows.

    Args:
        client: The Notion API client.
        database_id: The ID of the database to fetch.

    Returns:
        DatabaseData containing schema and all rows.
    """
    logger.debug(f"Fetching database {database_id}")

    database = client.get_database(database_id)
    rows = client.query_database(database_id)

    logger.debug(f"Database {database_id} has {len(rows)} rows")

    return DatabaseData(database=database, rows=rows)


def fetch_data_source_with_rows(client: NotionClient, data_source_id: str) -> DatabaseData:
    """Fetch a data source with its schema and all rows.

    Args:
        client: The Notion API client.
        data_source_id: The ID of the data source to fetch.

    Returns:
        DatabaseData containing schema and all rows.
    """
    logger.debug(f"Fetching data source {data_source_id}")

    data_source = client.get_data_source(data_source_id)
    rows = client.query_data_source(data_source_id)

    logger.debug(f"Data source {data_source_id} has {len(rows)} rows")

    return DatabaseData(database=data_source, rows=rows)

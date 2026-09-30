# ABOUTME: Tests that the Notion SDK's own logger stays silent and handler-free.
# ABOUTME: The app logs every request failure itself, as structured JSON.

import logging

import pytest

from notion_backup.notion.client import NotionClient

SDK_LOGGER = logging.getLogger("notion_client")


@pytest.fixture(autouse=True)
def clean_sdk_logger():
    SDK_LOGGER.handlers.clear()
    yield
    SDK_LOGGER.handlers.clear()
    SDK_LOGGER.setLevel(logging.NOTSET)


def test_clients_add_no_handlers_to_sdk_logger():
    NotionClient("token-a")
    NotionClient("token-b")

    assert SDK_LOGGER.handlers == []


def test_sdk_logger_ignores_request_warnings():
    NotionClient("token")

    assert not SDK_LOGGER.isEnabledFor(logging.WARNING)

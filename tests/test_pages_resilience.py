# ABOUTME: Tests that page block fetching survives permanently-inaccessible child blocks.
# ABOUTME: Inaccessible children are skipped; transient failures still propagate.

import httpx
import pytest

from notion_client.errors import APIErrorCode, APIResponseError, RequestTimeoutError

from notion_backup.notion.pages import fetch_blocks_recursive


def _api_error(status: int, code: APIErrorCode) -> APIResponseError:
    response = httpx.Response(status_code=status, headers={})
    return APIResponseError(response=response, message="boom", code=code)


class FakeClient:
    """Returns blocks per id from a map; raises configured errors for given ids."""

    def __init__(self, blocks_by_id: dict, errors_by_id: dict | None = None):
        self._blocks_by_id = blocks_by_id
        self._errors_by_id = errors_by_id or {}

    def get_blocks(self, block_id: str) -> list[dict]:
        if block_id in self._errors_by_id:
            raise self._errors_by_id[block_id]
        return self._blocks_by_id.get(block_id, [])


def test_skips_inaccessible_child_block_keeps_rest():
    parent = "page1"
    blocks_by_id = {
        parent: [
            {"id": "childA", "type": "paragraph", "has_children": True},
            {"id": "blockB", "type": "paragraph", "has_children": False},
        ],
    }
    errors_by_id = {"childA": _api_error(404, APIErrorCode.ObjectNotFound)}
    client = FakeClient(blocks_by_id, errors_by_id)

    result = fetch_blocks_recursive(client, parent)

    assert [b["id"] for b in result] == ["childA", "blockB"]
    assert "children" not in result[0]


def test_propagates_transient_child_failure():
    parent = "page1"
    blocks_by_id = {
        parent: [
            {"id": "childA", "type": "paragraph", "has_children": True},
        ],
    }
    errors_by_id = {"childA": RequestTimeoutError()}
    client = FakeClient(blocks_by_id, errors_by_id)

    with pytest.raises(RequestTimeoutError):
        fetch_blocks_recursive(client, parent)


def test_fetches_accessible_children():
    parent = "page1"
    blocks_by_id = {
        parent: [{"id": "childA", "type": "paragraph", "has_children": True}],
        "childA": [{"id": "grandchild", "type": "paragraph", "has_children": False}],
    }
    client = FakeClient(blocks_by_id)

    result = fetch_blocks_recursive(client, parent)

    assert result[0]["children"][0]["id"] == "grandchild"

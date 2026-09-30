# ABOUTME: Tests that page fetching survives inaccessible child blocks and synced database rows.
# ABOUTME: Unreadable content is skipped. Transient and unrecognised failures still propagate.

import httpx
import pytest

from notion_client.errors import APIErrorCode, APIResponseError, RequestTimeoutError

from notion_backup.notion.pages import fetch_blocks_recursive, fetch_page_with_blocks


def _api_error(status: int, code: APIErrorCode, message: str = "boom") -> APIResponseError:
    return APIResponseError(
        code=code,
        status=status,
        message=message,
        headers=httpx.Headers(),
        raw_body_text="",
    )


class FakeClient:
    """Returns blocks per id from a map; raises configured errors for given ids."""

    def __init__(self, blocks_by_id: dict, errors_by_id: dict | None = None):
        self._blocks_by_id = blocks_by_id
        self._errors_by_id = errors_by_id or {}

    def get_blocks(self, block_id: str) -> list[dict]:
        if block_id in self._errors_by_id:
            raise self._errors_by_id[block_id]
        return self._blocks_by_id.get(block_id, [])

    def get_page(self, page_id: str) -> dict:
        return {"id": page_id, "properties": {"Title": {"type": "title"}}}


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


SYNCED_ROW_REJECTION = "Block type external_object_instance_page is not supported via the API."


def test_synced_row_page_keeps_properties_with_empty_body():
    errors_by_id = {"row1": _api_error(400, APIErrorCode.ValidationError, SYNCED_ROW_REJECTION)}
    client = FakeClient({}, errors_by_id)

    result = fetch_page_with_blocks(client, "row1")

    assert result.page["id"] == "row1"
    assert result.page["properties"]
    assert result.blocks == []


def test_synced_row_child_is_skipped_keeps_rest():
    blocks_by_id = {
        "page1": [
            {"id": "childA", "type": "paragraph", "has_children": True},
            {"id": "blockB", "type": "paragraph", "has_children": False},
        ],
    }
    errors_by_id = {"childA": _api_error(400, APIErrorCode.ValidationError, SYNCED_ROW_REJECTION)}
    client = FakeClient(blocks_by_id, errors_by_id)

    result = fetch_blocks_recursive(client, "page1")

    assert [b["id"] for b in result] == ["childA", "blockB"]
    assert result[0]["children"] == []


def test_other_unsupported_type_still_raises():
    message = "Block type ai_block is not supported via the API."
    errors_by_id = {"page1": _api_error(400, APIErrorCode.ValidationError, message)}
    client = FakeClient({}, errors_by_id)

    with pytest.raises(APIResponseError):
        fetch_page_with_blocks(client, "page1")


def test_page_level_not_found_still_raises():
    errors_by_id = {"page1": _api_error(404, APIErrorCode.ObjectNotFound, SYNCED_ROW_REJECTION)}
    client = FakeClient({}, errors_by_id)

    with pytest.raises(APIResponseError):
        fetch_page_with_blocks(client, "page1")


def test_regular_page_keeps_its_blocks():
    blocks_by_id = {"page1": [{"id": "blockA", "type": "paragraph", "has_children": False}]}
    client = FakeClient(blocks_by_id)

    result = fetch_page_with_blocks(client, "page1")

    assert [b["id"] for b in result.blocks] == ["blockA"]

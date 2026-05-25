# ABOUTME: Tests that file URL extraction skips empty/blank URLs.
# ABOUTME: Empty Notion file blocks should not be queued for download.

from notion_backup.backup.files import extract_file_urls


def _file_block(block_id: str, url: str) -> dict:
    return {"id": block_id, "type": "file", "file": {"file": {"url": url}}}


def _external_block(block_id: str, url: str) -> dict:
    return {"id": block_id, "type": "image", "image": {"external": {"url": url}}}


def test_skips_empty_hosted_file_url():
    blocks = [
        _file_block("a", ""),
        _file_block("b", "https://example.com/doc.pdf"),
    ]
    urls = extract_file_urls(blocks)
    assert [u["block_id"] for u in urls] == ["b"]


def test_skips_empty_external_url():
    blocks = [
        _external_block("a", "   "),
        _external_block("b", "https://example.com/img.png"),
    ]
    urls = extract_file_urls(blocks)
    assert [u["block_id"] for u in urls] == ["b"]


def test_skips_empty_urls_in_nested_children():
    blocks = [
        {
            "id": "parent",
            "type": "paragraph",
            "children": [
                _file_block("empty", ""),
                _file_block("valid", "https://example.com/a.png"),
            ],
        }
    ]
    urls = extract_file_urls(blocks)
    assert [u["block_id"] for u in urls] == ["valid"]

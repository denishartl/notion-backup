# ABOUTME: Converts Notion blocks to Markdown format.
# ABOUTME: Handles all common block types with frontmatter generation.

import re
from datetime import datetime
from typing import Any

import yaml


def get_rich_text(rich_text: list[dict]) -> str:
    """Extract plain text from Notion rich_text array with formatting."""
    result = []
    for segment in rich_text:
        text = segment.get("plain_text", "")
        annotations = segment.get("annotations", {})

        # Apply formatting
        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"

        # Handle links
        if segment.get("href"):
            text = f"[{text}]({segment['href']})"

        result.append(text)

    return "".join(result)


def get_page_title(page: dict) -> str:
    """Extract title from page properties."""
    props = page.get("properties", {})
    if not props:
        return "Untitled"

    # Title property (for database pages)
    if "title" in props and props["title"]:
        return get_rich_text(props["title"].get("title", []))

    # Name property (common in databases)
    if "Name" in props and props["Name"] and props["Name"].get("type") == "title":
        return get_rich_text(props["Name"].get("title", []))

    # Check all properties for title type
    for prop in props.values():
        if prop and prop.get("type") == "title":
            return get_rich_text(prop.get("title", []))

    return "Untitled"


def block_to_markdown(block: dict, files_path: str = "files", indent: int = 0) -> str:
    """Convert a single Notion block to Markdown.

    Args:
        block: Notion block dict.
        files_path: Relative path to files directory.
        indent: Indentation level for nested content.

    Returns:
        Markdown string.
    """
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})
    prefix = "  " * indent

    # Paragraph
    if block_type == "paragraph":
        text = get_rich_text(block_data.get("rich_text", []))
        return f"{prefix}{text}\n"

    # Headings
    if block_type == "heading_1":
        text = get_rich_text(block_data.get("rich_text", []))
        return f"{prefix}# {text}\n"

    if block_type == "heading_2":
        text = get_rich_text(block_data.get("rich_text", []))
        return f"{prefix}## {text}\n"

    if block_type == "heading_3":
        text = get_rich_text(block_data.get("rich_text", []))
        return f"{prefix}### {text}\n"

    # Lists
    if block_type == "bulleted_list_item":
        text = get_rich_text(block_data.get("rich_text", []))
        result = f"{prefix}- {text}\n"
        if "children" in block:
            result += blocks_to_markdown(block["children"], files_path, indent + 1)
        return result

    if block_type == "numbered_list_item":
        text = get_rich_text(block_data.get("rich_text", []))
        result = f"{prefix}1. {text}\n"
        if "children" in block:
            result += blocks_to_markdown(block["children"], files_path, indent + 1)
        return result

    # To-do
    if block_type == "to_do":
        text = get_rich_text(block_data.get("rich_text", []))
        checked = block_data.get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        result = f"{prefix}- {checkbox} {text}\n"
        if "children" in block:
            result += blocks_to_markdown(block["children"], files_path, indent + 1)
        return result

    # Toggle
    if block_type == "toggle":
        text = get_rich_text(block_data.get("rich_text", []))
        result = f"{prefix}<details>\n{prefix}<summary>{text}</summary>\n\n"
        if "children" in block:
            result += blocks_to_markdown(block["children"], files_path, indent)
        result += f"{prefix}</details>\n"
        return result

    # Quote
    if block_type == "quote":
        text = get_rich_text(block_data.get("rich_text", []))
        lines = text.split("\n")
        result = "\n".join(f"{prefix}> {line}" for line in lines) + "\n"
        if "children" in block:
            result += blocks_to_markdown(block["children"], files_path, indent + 1)
        return result

    # Callout
    if block_type == "callout":
        text = get_rich_text(block_data.get("rich_text", []))
        icon = block_data.get("icon") or {}
        emoji = icon.get("emoji", "💡") if icon.get("type") == "emoji" else "💡"
        result = f"{prefix}> {emoji} {text}\n"
        if "children" in block:
            result += blocks_to_markdown(block["children"], files_path, indent + 1)
        return result

    # Code
    if block_type == "code":
        text = get_rich_text(block_data.get("rich_text", []))
        language = block_data.get("language", "")
        return f"{prefix}```{language}\n{text}\n{prefix}```\n"

    # Divider
    if block_type == "divider":
        return f"{prefix}---\n"

    # Image
    if block_type == "image":
        caption = get_rich_text(block_data.get("caption", []))
        alt_text = caption or "image"
        # Reference the files directory
        if "file" in block_data:
            url = block_data["file"].get("url", "")
            # Extract filename from URL for local reference
            return f"{prefix}![{alt_text}]({files_path}/{_url_to_filename(url, block.get('id', ''))})\n"
        elif "external" in block_data:
            url = block_data["external"].get("url", "")
            return f"{prefix}![{alt_text}]({url})\n"
        return f"{prefix}![{alt_text}](missing-image)\n"

    # File/PDF/Video/Audio
    if block_type in ("file", "pdf", "video", "audio"):
        caption = get_rich_text(block_data.get("caption", []))
        name = caption or block_type
        if "file" in block_data:
            url = block_data["file"].get("url", "")
            filename = _url_to_filename(url, block.get("id", ""))
            return f"{prefix}[{name}]({files_path}/{filename})\n"
        elif "external" in block_data:
            url = block_data["external"].get("url", "")
            return f"{prefix}[{name}]({url})\n"
        return f"{prefix}[{name}](missing-file)\n"

    # Bookmark
    if block_type == "bookmark":
        url = block_data.get("url", "")
        caption = get_rich_text(block_data.get("caption", []))
        title = caption or url
        return f"{prefix}[{title}]({url})\n"

    # Table
    if block_type == "table":
        if "children" not in block:
            return ""
        rows = block["children"]
        if not rows:
            return ""

        result = []
        for i, row in enumerate(rows):
            if row.get("type") != "table_row":
                continue
            cells = row.get("table_row", {}).get("cells", [])
            cell_texts = [get_rich_text(cell) for cell in cells]
            result.append(f"{prefix}| " + " | ".join(cell_texts) + " |")
            if i == 0:
                # Add header separator
                result.append(f"{prefix}|" + "|".join(["---"] * len(cells)) + "|")

        return "\n".join(result) + "\n"

    # Column list
    if block_type == "column_list":
        if "children" in block:
            return blocks_to_markdown(block["children"], files_path, indent)
        return ""

    # Column
    if block_type == "column":
        if "children" in block:
            return blocks_to_markdown(block["children"], files_path, indent)
        return ""

    # Equation
    if block_type == "equation":
        expression = block_data.get("expression", "")
        return f"{prefix}$$\n{expression}\n$$\n"

    # Link preview / embed
    if block_type in ("link_preview", "embed"):
        url = block_data.get("url", "")
        return f"{prefix}[{url}]({url})\n"

    # Synced block
    if block_type == "synced_block":
        if "children" in block:
            return blocks_to_markdown(block["children"], files_path, indent)
        return ""

    # Child page (just note it exists)
    if block_type == "child_page":
        title = block_data.get("title", "Untitled")
        return f"{prefix}📄 [{title}]()\n"

    # Child database
    if block_type == "child_database":
        title = block_data.get("title", "Untitled Database")
        return f"{prefix}🗃️ [{title}]()\n"

    # Table of contents
    if block_type == "table_of_contents":
        return f"{prefix}[Table of Contents]\n"

    # Breadcrumb
    if block_type == "breadcrumb":
        return ""  # Skip breadcrumbs

    # Unknown block type
    return f"{prefix}<!-- Unsupported block type: {block_type} -->\n"


def _url_to_filename(url: str, block_id: str) -> str:
    """Generate filename from URL matching the download logic."""
    import hashlib
    from pathlib import Path
    from urllib.parse import urlparse, unquote

    parsed = urlparse(url)
    path = unquote(parsed.path)
    original_name = Path(path).name

    if "?" in original_name:
        original_name = original_name.split("?")[0]

    if not original_name or original_name == "/":
        original_name = "file"

    hash_input = f"{block_id}:{url}"
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

    return f"{short_hash}-{original_name}"


def blocks_to_markdown(blocks: list[dict], files_path: str = "files", indent: int = 0) -> str:
    """Convert a list of Notion blocks to Markdown.

    Args:
        blocks: List of Notion block dicts.
        files_path: Relative path to files directory.
        indent: Base indentation level.

    Returns:
        Markdown string.
    """
    result = []
    for block in blocks:
        md = block_to_markdown(block, files_path, indent)
        if md:
            result.append(md)

    return "\n".join(result)


def extract_property_value(prop: dict) -> Any:
    """Extract a simple value from a Notion property."""
    if not prop:
        return None
    prop_type = prop.get("type")

    if prop_type == "title":
        return get_rich_text(prop.get("title", []))
    if prop_type == "rich_text":
        return get_rich_text(prop.get("rich_text", []))
    if prop_type == "number":
        return prop.get("number")
    if prop_type == "select":
        select = prop.get("select")
        return select.get("name") if select else None
    if prop_type == "multi_select":
        return [s.get("name") for s in prop.get("multi_select", [])]
    if prop_type == "date":
        date = prop.get("date")
        if date:
            return date.get("start")
        return None
    if prop_type == "checkbox":
        return prop.get("checkbox")
    if prop_type == "url":
        return prop.get("url")
    if prop_type == "email":
        return prop.get("email")
    if prop_type == "phone_number":
        return prop.get("phone_number")
    if prop_type == "status":
        status = prop.get("status")
        return status.get("name") if status else None
    if prop_type == "people":
        return [p.get("name", p.get("id")) for p in prop.get("people", [])]
    if prop_type == "files":
        return [f.get("name", "file") for f in prop.get("files", [])]
    if prop_type == "relation":
        return [r.get("id") for r in prop.get("relation", [])]
    if prop_type == "formula":
        formula = prop.get("formula", {})
        formula_type = formula.get("type")
        return formula.get(formula_type)
    if prop_type == "rollup":
        rollup = prop.get("rollup", {})
        rollup_type = rollup.get("type")
        return rollup.get(rollup_type)
    if prop_type == "created_time":
        return prop.get("created_time")
    if prop_type == "created_by":
        return prop.get("created_by", {}).get("name")
    if prop_type == "last_edited_time":
        return prop.get("last_edited_time")
    if prop_type == "last_edited_by":
        return prop.get("last_edited_by", {}).get("name")

    return None


def page_to_frontmatter(page: dict) -> str:
    """Generate YAML frontmatter from page metadata.

    Args:
        page: Notion page dict.

    Returns:
        YAML frontmatter string including delimiters.
    """
    metadata = {
        "notion_id": page.get("id", ""),
        "created": page.get("created_time", ""),
        "last_edited": page.get("last_edited_time", ""),
    }

    # Extract properties
    props = page.get("properties", {})
    properties = {}

    for name, prop in props.items():
        if not prop:
            continue
        # Skip title property (it's the page title)
        if prop.get("type") == "title":
            continue

        value = extract_property_value(prop)
        if value is not None:
            properties[name] = value

    if properties:
        metadata["properties"] = properties

    # Generate YAML
    yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return f"---\n{yaml_str}---\n\n"

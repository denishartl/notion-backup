# ABOUTME: Writes Markdown files with directory hierarchy matching page nesting.
# ABOUTME: Handles safe filename generation and nested page structure.

import logging
import re
from pathlib import Path

from .converter import blocks_to_markdown, page_to_frontmatter, get_page_title

logger = logging.getLogger(__name__)


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Convert a string to a safe filename.

    Args:
        name: The original name.
        max_length: Maximum filename length.

    Returns:
        Sanitized filename.
    """
    # Replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', "-", name)
    safe = re.sub(r"\s+", " ", safe)
    safe = safe.strip(". ")

    if not safe:
        safe = "Untitled"

    if len(safe) > max_length:
        safe = safe[:max_length].rstrip(". ")

    return safe


class MarkdownWriter:
    """Writes Markdown files for backed up pages."""

    def __init__(self, markdown_path: Path, files_path: Path):
        """Initialize the writer.

        Args:
            markdown_path: Base path for markdown files.
            files_path: Path where files are stored (for relative links).
        """
        self.markdown_path = markdown_path
        self.files_path = files_path
        self._page_paths: dict[str, Path] = {}

    def _get_relative_files_path(self, md_file_path: Path) -> str:
        """Get relative path from markdown file to files directory."""
        try:
            rel_path = Path("..") / self.files_path.relative_to(self.markdown_path.parent)
            return str(rel_path)
        except ValueError:
            # Fallback if paths don't share a common base
            return "../files"

    def write_page(
        self,
        page: dict,
        blocks: list[dict],
        parent_id: str | None = None,
    ) -> Path:
        """Write a page as Markdown.

        Args:
            page: Notion page dict.
            blocks: List of blocks in the page.
            parent_id: Parent page ID for nesting (optional).

        Returns:
            Path to the written file.
        """
        page_id = page.get("id", "unknown")
        title = get_page_title(page)
        safe_title = sanitize_filename(title)

        # Determine directory based on parent
        if parent_id and parent_id in self._page_paths:
            parent_dir = self._page_paths[parent_id]
            if parent_dir.suffix == ".md":
                # Convert parent file to directory
                parent_dir = parent_dir.with_suffix("")
            output_dir = parent_dir
        else:
            output_dir = self.markdown_path

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create file path
        file_path = output_dir / f"{safe_title}.md"

        # Handle duplicate filenames
        counter = 1
        original_path = file_path
        while file_path.exists():
            file_path = original_path.with_stem(f"{original_path.stem} ({counter})")
            counter += 1

        # Generate content
        files_rel_path = self._get_relative_files_path(file_path)
        frontmatter = page_to_frontmatter(page)
        heading = f"# {title}\n\n"
        content = blocks_to_markdown(blocks, files_rel_path)

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter)
            f.write(heading)
            f.write(content)

        self._page_paths[page_id] = file_path
        logger.debug(f"Wrote markdown: {file_path}")

        return file_path

    def get_page_path(self, page_id: str) -> Path | None:
        """Get the path where a page was written."""
        return self._page_paths.get(page_id)

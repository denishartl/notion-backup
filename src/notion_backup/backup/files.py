# ABOUTME: File download logic for embedded images and attachments.
# ABOUTME: Extracts file URLs from blocks and downloads them.

import hashlib
import logging
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

logger = logging.getLogger(__name__)

# Block types that can contain files
FILE_BLOCK_TYPES = {"image", "video", "file", "pdf", "audio"}

# Timeout for file downloads (seconds)
DOWNLOAD_TIMEOUT = 30

# Max retries for failed downloads
MAX_RETRIES = 3


def extract_file_urls(blocks: list[dict], urls: list[dict] | None = None) -> list[dict]:
    """Extract all file URLs from blocks recursively.

    Args:
        blocks: List of Notion blocks.
        urls: Accumulator for recursive calls.

    Returns:
        List of dicts with 'url', 'block_id', and 'type' keys.
    """
    if urls is None:
        urls = []

    for block in blocks:
        block_type = block.get("type")
        block_id = block.get("id", "unknown")

        if block_type in FILE_BLOCK_TYPES:
            block_data = block.get(block_type, {})

            # Files can be external or hosted by Notion
            if "file" in block_data:
                urls.append({
                    "url": block_data["file"]["url"],
                    "block_id": block_id,
                    "type": block_type,
                })
            elif "external" in block_data:
                urls.append({
                    "url": block_data["external"]["url"],
                    "block_id": block_id,
                    "type": block_type,
                })

        # Recursively check children
        if "children" in block:
            extract_file_urls(block["children"], urls)

    return urls


def generate_filename(url: str, block_id: str) -> str:
    """Generate a unique filename for a downloaded file.

    Uses a hash prefix for uniqueness and preserves original extension.

    Args:
        url: The file URL.
        block_id: The block ID containing the file.

    Returns:
        Filename in format: {hash}-{original_name}
    """
    parsed = urlparse(url)
    path = unquote(parsed.path)
    original_name = Path(path).name

    # Clean up the name (Notion URLs can have query params in the name)
    if "?" in original_name:
        original_name = original_name.split("?")[0]

    # If no filename, use a generic one
    if not original_name or original_name == "/":
        original_name = "file"

    # Create a short hash for uniqueness
    hash_input = f"{block_id}:{url}"
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

    return f"{short_hash}-{original_name}"


def download_file(url: str, destination: Path) -> bool:
    """Download a file from URL to destination.

    Args:
        url: The file URL.
        destination: Path to save the file.

    Returns:
        True if successful, False otherwise.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
            response.raise_for_status()

            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True

        except requests.RequestException as e:
            logger.warning(f"Download attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                return False

    return False


def download_files_from_blocks(
    blocks: list[dict],
    files_path: Path,
) -> tuple[int, list[dict]]:
    """Download all files referenced in blocks.

    Args:
        blocks: List of Notion blocks (can include nested children).
        files_path: Directory to save files to.

    Returns:
        Tuple of (count of successful downloads, list of error dicts).
    """
    file_urls = extract_file_urls(blocks)
    downloaded = 0
    errors = []

    for file_info in file_urls:
        url = file_info["url"]
        block_id = file_info["block_id"]
        filename = generate_filename(url, block_id)
        destination = files_path / filename

        logger.debug(f"Downloading {filename}")

        if download_file(url, destination):
            downloaded += 1
        else:
            errors.append({
                "type": "file",
                "url": url,
                "block_id": block_id,
                "error": "Download failed after retries",
            })
            logger.warning(f"Failed to download file from block {block_id}")

    logger.info(f"Downloaded {downloaded}/{len(file_urls)} files")
    return downloaded, errors

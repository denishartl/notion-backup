# ABOUTME: File download logic for embedded images and attachments.
# ABOUTME: Extracts file URLs from blocks and downloads them concurrently.

import hashlib
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

logger = logging.getLogger(__name__)

# Number of concurrent file downloads
MAX_DOWNLOAD_WORKERS = 10

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


def _is_hex_string(s: str) -> bool:
    """Check if string contains only hexadecimal characters."""
    if len(s) % 2 != 0:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def generate_filename(url: str, block_id: str) -> str:
    """Generate a unique filename for a downloaded file.

    Uses a hash prefix for uniqueness and preserves original extension.
    Handles Notion's image proxy which hex-encodes external URLs in the path.

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

    # Detect hex-encoded URLs (common with Notion's image proxy for external images)
    if len(original_name) > 50 and _is_hex_string(original_name):
        try:
            decoded = bytes.fromhex(original_name).decode("utf-8")
            if decoded.startswith(("http://", "https://")):
                decoded_parsed = urlparse(decoded)
                decoded_name = Path(unquote(decoded_parsed.path)).name
                if decoded_name and decoded_name != "/":
                    original_name = decoded_name.split("?")[0] if "?" in decoded_name else decoded_name
        except (ValueError, UnicodeDecodeError):
            pass  # Not valid hex or not decodable

    # If no filename, use a generic one
    if not original_name or original_name == "/":
        original_name = "file"

    # Create a short hash for uniqueness
    hash_input = f"{block_id}:{url}"
    short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

    # Truncate if still too long (filesystem limit is 255, stay well under)
    max_name_len = 200 - len(short_hash) - 1
    if len(original_name) > max_name_len:
        ext = Path(original_name).suffix
        if ext:
            base = original_name[: max_name_len - len(ext) - 3]
            original_name = f"{base}...{ext}"
        else:
            original_name = original_name[: max_name_len - 3] + "..."

    return f"{short_hash}-{original_name}"


def download_file(url: str, destination: Path) -> int:
    """Download a file from URL to destination.

    Args:
        url: The file URL.
        destination: Path to save the file.

    Returns:
        File size in bytes if successful, -1 otherwise.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
            response.raise_for_status()

            size = 0
            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    size += len(chunk)

            return size

        except requests.RequestException as e:
            logger.warning(f"Download attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                return -1

    return -1


def download_files_from_blocks(
    blocks: list[dict],
    files_path: Path,
) -> tuple[int, int, list[dict]]:
    """Download all files referenced in blocks concurrently.

    Args:
        blocks: List of Notion blocks (can include nested children).
        files_path: Directory to save files to.

    Returns:
        Tuple of (count of successful downloads, total bytes downloaded, list of error dicts).
    """
    file_urls = extract_file_urls(blocks)

    if not file_urls:
        return 0, 0, []

    downloaded = 0
    total_size = 0
    completed = 0
    errors = []
    lock = threading.Lock()
    total_files = len(file_urls)

    def download_one(file_info: dict) -> None:
        """Download a single file and update shared counters."""
        nonlocal downloaded, total_size, completed
        url = file_info["url"]
        block_id = file_info["block_id"]
        filename = generate_filename(url, block_id)
        destination = files_path / filename

        logger.debug(f"Downloading {filename}")

        size = download_file(url, destination)
        with lock:
            completed += 1
            if size >= 0:
                downloaded += 1
                total_size += size
            else:
                errors.append({
                    "type": "file",
                    "url": url,
                    "block_id": block_id,
                    "error": "Download failed after retries",
                })
                logger.warning(f"Failed to download file from block {block_id}")

            # Log progress every 10 files or at the end
            if completed == total_files or completed % 10 == 0:
                logger.info(f"Downloading files... {completed}/{total_files}")

    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
        futures = [executor.submit(download_one, info) for info in file_urls]
        for future in as_completed(futures):
            # Propagate any unexpected exceptions
            future.result()

    return downloaded, total_size, errors

# ABOUTME: Directory and file management for backups.
# ABOUTME: Creates timestamped backup directories and saves JSON files.

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupStorage:
    """Manages backup directory structure and file storage."""

    def __init__(self, base_path: Path, workspace_name: str):
        """Initialize storage for a backup run.

        Args:
            base_path: Base path for all backups (e.g., /data/backups).
            workspace_name: Name of the workspace being backed up.
        """
        self.base_path = base_path
        self.workspace_name = workspace_name
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.backup_path = base_path / workspace_name / self.timestamp

        # Create directory structure
        self.json_pages_path = self.backup_path / "json" / "pages"
        self.json_databases_path = self.backup_path / "json" / "databases"
        self.markdown_path = self.backup_path / "markdown"
        self.files_path = self.backup_path / "files"

    def create_directories(self) -> None:
        """Create all backup directories."""
        for path in [
            self.json_pages_path,
            self.json_databases_path,
            self.markdown_path,
            self.files_path,
        ]:
            path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created backup directory: {self.backup_path}")

    def save_page_json(self, page_id: str, data: dict) -> Path:
        """Save page data as JSON.

        Args:
            page_id: The Notion page ID.
            data: Complete page data including blocks.

        Returns:
            Path to the saved file.
        """
        file_path = self.json_pages_path / f"{page_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return file_path

    def save_database_json(self, database_id: str, data: dict) -> Path:
        """Save database data as JSON.

        Args:
            database_id: The Notion database ID.
            data: Complete database data including schema and rows.

        Returns:
            Path to the saved file.
        """
        file_path = self.json_databases_path / f"{database_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return file_path

    def save_manifest(self, manifest: dict) -> Path:
        """Save the backup manifest.

        Args:
            manifest: Manifest data.

        Returns:
            Path to the saved file.
        """
        file_path = self.backup_path / "manifest.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return file_path

    def get_file_path(self, filename: str) -> Path:
        """Get path for saving a downloaded file.

        Args:
            filename: Name of the file.

        Returns:
            Full path in the files directory.
        """
        return self.files_path / filename

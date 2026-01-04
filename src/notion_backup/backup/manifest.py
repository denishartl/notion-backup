# ABOUTME: Manifest generation for backup runs.
# ABOUTME: Creates a JSON summary of backup contents and status.

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal


@dataclass
class BackupManifest:
    """Manifest for a single backup run."""

    timestamp: str = ""
    duration_seconds: float = 0.0
    pages_backed_up: int = 0
    databases_backed_up: int = 0
    files_downloaded: int = 0
    errors: list[dict] = field(default_factory=list)
    status: Literal["completed", "completed_with_warnings", "failed"] = "completed"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        """Convert manifest to dictionary for JSON serialization."""
        return asdict(self)


def create_manifest(
    start_time: datetime,
    pages_count: int,
    databases_count: int,
    files_count: int,
    errors: list[dict],
) -> BackupManifest:
    """Create a backup manifest.

    Args:
        start_time: When the backup started.
        pages_count: Number of pages backed up.
        databases_count: Number of databases backed up.
        files_count: Number of files downloaded.
        errors: List of error dicts from the backup.

    Returns:
        BackupManifest with computed fields.
    """
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    # Determine status based on errors
    if errors:
        # Check if all items failed
        total_items = pages_count + databases_count + files_count
        if total_items == 0 and errors:
            status = "failed"
        else:
            status = "completed_with_warnings"
    else:
        status = "completed"

    return BackupManifest(
        timestamp=start_time.isoformat() + "Z",
        duration_seconds=round(duration, 2),
        pages_backed_up=pages_count,
        databases_backed_up=databases_count,
        files_downloaded=files_count,
        errors=errors,
        status=status,
    )

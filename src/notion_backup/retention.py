# ABOUTME: Backup retention management.
# ABOUTME: Deletes old backups beyond the configured retention count.

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def get_backup_dirs(workspace_path: Path) -> list[Path]:
    """Get all backup directories for a workspace, sorted by name (oldest first).

    Args:
        workspace_path: Path to workspace backup directory.

    Returns:
        List of backup directory paths, sorted oldest to newest.
    """
    if not workspace_path.exists():
        return []

    # Backup directories are named with timestamps: YYYY-MM-DD_HHMMSS
    dirs = [
        d for d in workspace_path.iterdir()
        if d.is_dir() and _is_backup_dir(d.name)
    ]

    return sorted(dirs, key=lambda d: d.name)


def _is_backup_dir(name: str) -> bool:
    """Check if a directory name matches backup timestamp format."""
    # Format: YYYY-MM-DD_HHMMSS (e.g., 2024-01-15_030000)
    if len(name) != 17:
        return False
    if name[4] != "-" or name[7] != "-" or name[10] != "_":
        return False
    # Check that other positions are digits
    digits = name[:4] + name[5:7] + name[8:10] + name[11:]
    return digits.isdigit()


def prune_old_backups(backups_path: Path, workspace_name: str, retention_count: int) -> int:
    """Delete old backups beyond retention count.

    Args:
        backups_path: Base path for all backups.
        workspace_name: Name of the workspace.
        retention_count: Number of backups to keep.

    Returns:
        Number of backups deleted.
    """
    workspace_path = backups_path / workspace_name
    backup_dirs = get_backup_dirs(workspace_path)

    # Calculate how many to delete
    to_delete = len(backup_dirs) - retention_count
    if to_delete <= 0:
        logger.debug(f"No backups to prune for {workspace_name} ({len(backup_dirs)}/{retention_count})")
        return 0

    deleted = 0
    for backup_dir in backup_dirs[:to_delete]:
        try:
            shutil.rmtree(backup_dir)
            logger.info(f"Deleted old backup: {backup_dir}")
            deleted += 1
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_dir}: {e}")

    return deleted

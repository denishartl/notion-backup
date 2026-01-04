# ABOUTME: Discord webhook notifications for backup status.
# ABOUTME: Sends summaries on completion or error based on configuration.

import logging
from typing import Literal

import requests

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10  # seconds


def send_discord_notification(
    webhook_url: str,
    workspace_name: str,
    status: Literal["completed", "completed_with_warnings", "failed"],
    pages: int,
    databases: int,
    files: int,
    duration_seconds: float,
    errors: list[dict],
    backup_path: str,
) -> bool:
    """Send backup notification to Discord.

    Args:
        webhook_url: Discord webhook URL.
        workspace_name: Name of the backed up workspace.
        status: Backup status.
        pages: Number of pages backed up.
        databases: Number of databases backed up.
        files: Number of files downloaded.
        duration_seconds: Backup duration.
        errors: List of error dicts.
        backup_path: Path where backup was saved.

    Returns:
        True if notification sent successfully.
    """
    # Choose color based on status
    colors = {
        "completed": 0x00FF00,  # Green
        "completed_with_warnings": 0xFFFF00,  # Yellow
        "failed": 0xFF0000,  # Red
    }
    color = colors.get(status, 0x808080)

    # Choose emoji based on status
    emojis = {
        "completed": "✅",
        "completed_with_warnings": "⚠️",
        "failed": "❌",
    }
    emoji = emojis.get(status, "📦")

    # Format duration
    minutes = int(duration_seconds // 60)
    seconds = int(duration_seconds % 60)
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    # Build description
    description_lines = [
        f"**Pages:** {pages}",
        f"**Databases:** {databases}",
        f"**Files:** {files}",
        f"**Duration:** {duration_str}",
    ]

    if errors:
        error_count = len(errors)
        description_lines.append(f"**Errors:** {error_count}")

        # Show first few errors
        if error_count <= 3:
            for err in errors:
                err_type = err.get("type", "unknown")
                err_id = err.get("id", err.get("url", "unknown"))
                description_lines.append(f"  • {err_type}: {err_id}")
        else:
            for err in errors[:2]:
                err_type = err.get("type", "unknown")
                err_id = err.get("id", err.get("url", "unknown"))
                description_lines.append(f"  • {err_type}: {err_id}")
            description_lines.append(f"  • ... and {error_count - 2} more")

    description = "\n".join(description_lines)

    # Build embed
    embed = {
        "title": f"{emoji} Notion Backup: {workspace_name}",
        "description": description,
        "color": color,
        "footer": {
            "text": f"Status: {status}",
        },
    }

    payload = {
        "embeds": [embed],
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
        )
        response.raise_for_status()
        logger.info(f"Sent Discord notification for {workspace_name}")
        return True

    except requests.RequestException as e:
        logger.error(f"Failed to send Discord notification: {e}")
        return False


def should_notify(notify_on: str, status: str) -> bool:
    """Determine if a notification should be sent.

    Args:
        notify_on: Notification mode ("always" or "error").
        status: Backup status.

    Returns:
        True if notification should be sent.
    """
    if notify_on == "always":
        return True

    if notify_on == "error":
        return status in ("completed_with_warnings", "failed")

    return False

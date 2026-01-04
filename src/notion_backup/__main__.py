# ABOUTME: CLI entry point for notion-backup.
# ABOUTME: Provides 'serve' and 'run' commands.

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import load_config, ConfigError, WorkspaceConfig
from .scheduler import run_scheduler
from .notion import NotionClient, fetch_page_with_blocks, fetch_database_with_rows
from .backup import BackupStorage, download_files_from_blocks, create_manifest


DEFAULT_CONFIG_PATH = Path("/data/config.yaml")
DEFAULT_BACKUP_PATH = Path("/data/backups")


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def backup_workspace(ws: WorkspaceConfig, backup_path: Path) -> dict:
    """Backup a single workspace and return statistics.

    Args:
        ws: Workspace configuration.
        backup_path: Base path for backups.

    Returns:
        Dict with backup statistics and manifest.
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.utcnow()

    token = ws.get_token()
    client = NotionClient(token)

    # Initialize storage
    storage = BackupStorage(backup_path, ws.name)
    storage.create_directories()

    # Discover all content
    content = client.discover_content()

    pages_data = []
    databases_data = []
    errors = []
    all_blocks = []

    # Fetch all pages with their blocks
    for page in content.pages:
        page_id = page["id"]
        try:
            data = fetch_page_with_blocks(client, page_id)
            pages_data.append(data)
            all_blocks.extend(data.blocks)

            # Save page JSON
            storage.save_page_json(page_id, {
                "page": data.page,
                "blocks": data.blocks,
            })
            logger.debug(f"Saved page {page_id}")
        except Exception as e:
            logger.warning(f"Failed to fetch page {page_id}: {e}")
            errors.append({"type": "page", "id": page_id, "error": str(e)})

    # Fetch all databases with their rows
    for db in content.databases:
        db_id = db["id"]
        try:
            data = fetch_database_with_rows(client, db_id)
            databases_data.append(data)

            # Save database JSON
            storage.save_database_json(db_id, {
                "database": data.database,
                "rows": data.rows,
            })
            logger.debug(f"Saved database {db_id}")
        except Exception as e:
            logger.warning(f"Failed to fetch database {db_id}: {e}")
            errors.append({"type": "database", "id": db_id, "error": str(e)})

    # Download embedded files
    files_downloaded, file_errors = download_files_from_blocks(
        all_blocks,
        storage.files_path,
    )
    errors.extend(file_errors)

    # Create and save manifest
    manifest = create_manifest(
        start_time=start_time,
        pages_count=len(pages_data),
        databases_count=len(databases_data),
        files_count=files_downloaded,
        errors=errors,
    )
    storage.save_manifest(manifest.to_dict())

    logger.info(
        f"Workspace '{ws.name}': {manifest.pages_backed_up} pages, "
        f"{manifest.databases_backed_up} databases, "
        f"{manifest.files_downloaded} files, "
        f"{len(errors)} errors [{manifest.status}]"
    )

    return {
        "pages": manifest.pages_backed_up,
        "databases": manifest.databases_backed_up,
        "files": manifest.files_downloaded,
        "errors": len(errors),
        "status": manifest.status,
        "backup_path": str(storage.backup_path),
    }


def run_backup(config, workspace_name: str | None = None, backup_path: Path | None = None) -> None:
    """Execute backup for configured workspaces.

    Args:
        config: Application configuration.
        workspace_name: If provided, only backup this workspace.
        backup_path: Override default backup path.
    """
    logger = logging.getLogger(__name__)

    if backup_path is None:
        backup_path = DEFAULT_BACKUP_PATH

    workspaces = config.workspaces
    if workspace_name:
        workspaces = [ws for ws in workspaces if ws.name == workspace_name]
        if not workspaces:
            logger.error(f"Workspace '{workspace_name}' not found in config")
            sys.exit(1)

    for ws in workspaces:
        logger.info(f"Starting backup for workspace: {ws.name}")
        try:
            stats = backup_workspace(ws, backup_path)
            logger.info(f"Backup saved to: {stats['backup_path']}")
        except Exception as e:
            logger.error(f"Backup for workspace '{ws.name}' failed: {e}")


def cmd_serve(args: argparse.Namespace) -> None:
    """Run the scheduler and wait for cron triggers."""
    logger = logging.getLogger(__name__)

    try:
        config = load_config(args.config)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    logger.info(f"Loaded config with {len(config.workspaces)} workspace(s)")

    # Derive backup path from config location
    backup_path = args.config.parent / "backups"

    def scheduled_backup(cfg):
        run_backup(cfg, backup_path=backup_path)

    run_scheduler(config, scheduled_backup)


def cmd_run(args: argparse.Namespace) -> None:
    """Run backup immediately."""
    logger = logging.getLogger(__name__)

    try:
        config = load_config(args.config)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    logger.info(f"Loaded config with {len(config.workspaces)} workspace(s)")

    # Derive backup path from config location
    backup_path = args.config.parent / "backups"

    run_backup(config, workspace_name=args.workspace, backup_path=backup_path)


def main() -> None:
    """Main entry point."""
    setup_logging()

    parser = argparse.ArgumentParser(
        prog="notion-backup",
        description="Automated backup service for Notion workspaces",
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to config file (default: {DEFAULT_CONFIG_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve command
    subparsers.add_parser(
        "serve",
        help="Run scheduler and wait for cron triggers",
    )

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run backup immediately",
    )
    run_parser.add_argument(
        "--workspace", "-w",
        help="Only backup this workspace",
    )

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()

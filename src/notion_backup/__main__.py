# ABOUTME: CLI entry point for notion-backup.
# ABOUTME: Provides 'serve' and 'run' commands.

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config, ConfigError, WorkspaceConfig
from .scheduler import run_scheduler
from .notion import NotionClient, fetch_page_with_blocks, fetch_database_with_rows


DEFAULT_CONFIG_PATH = Path("/data/config.yaml")


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def backup_workspace(ws: WorkspaceConfig) -> dict:
    """Backup a single workspace and return statistics.

    Args:
        ws: Workspace configuration.

    Returns:
        Dict with backup statistics.
    """
    logger = logging.getLogger(__name__)

    token = ws.get_token()
    client = NotionClient(token)

    # Discover all content
    content = client.discover_content()

    pages_data = []
    databases_data = []
    errors = []

    # Fetch all pages with their blocks
    for page in content.pages:
        page_id = page["id"]
        try:
            data = fetch_page_with_blocks(client, page_id)
            pages_data.append(data)
            logger.debug(f"Fetched page {page_id} with {len(data.blocks)} blocks")
        except Exception as e:
            logger.warning(f"Failed to fetch page {page_id}: {e}")
            errors.append({"type": "page", "id": page_id, "error": str(e)})

    # Fetch all databases with their rows
    for db in content.databases:
        db_id = db["id"]
        try:
            data = fetch_database_with_rows(client, db_id)
            databases_data.append(data)
            logger.debug(f"Fetched database {db_id} with {len(data.rows)} rows")
        except Exception as e:
            logger.warning(f"Failed to fetch database {db_id}: {e}")
            errors.append({"type": "database", "id": db_id, "error": str(e)})

    stats = {
        "pages": len(pages_data),
        "databases": len(databases_data),
        "errors": len(errors),
    }

    logger.info(
        f"Workspace '{ws.name}': {stats['pages']} pages, "
        f"{stats['databases']} databases, {stats['errors']} errors"
    )

    # TODO: Phase 3 - Save to disk
    return stats


def run_backup(config, workspace_name: str | None = None) -> None:
    """Execute backup for configured workspaces.

    Args:
        config: Application configuration.
        workspace_name: If provided, only backup this workspace.
    """
    logger = logging.getLogger(__name__)

    workspaces = config.workspaces
    if workspace_name:
        workspaces = [ws for ws in workspaces if ws.name == workspace_name]
        if not workspaces:
            logger.error(f"Workspace '{workspace_name}' not found in config")
            sys.exit(1)

    for ws in workspaces:
        logger.info(f"Starting backup for workspace: {ws.name}")
        try:
            stats = backup_workspace(ws)
            logger.info(f"Backup for workspace '{ws.name}' completed")
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
    run_scheduler(config, run_backup)


def cmd_run(args: argparse.Namespace) -> None:
    """Run backup immediately."""
    logger = logging.getLogger(__name__)

    try:
        config = load_config(args.config)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    logger.info(f"Loaded config with {len(config.workspaces)} workspace(s)")
    run_backup(config, workspace_name=args.workspace)


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

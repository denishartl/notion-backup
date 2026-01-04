# ABOUTME: CLI entry point for notion-backup.
# ABOUTME: Provides 'serve' and 'run' commands.

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config, ConfigError
from .scheduler import run_scheduler


DEFAULT_CONFIG_PATH = Path("/data/config.yaml")


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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
        # TODO: Phase 2 - Implement actual backup logic
        logger.info(f"Backup for workspace '{ws.name}' completed (stub)")


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

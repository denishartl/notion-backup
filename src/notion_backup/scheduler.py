# ABOUTME: Cron-based job scheduling using APScheduler.
# ABOUTME: Manages scheduled backup execution.

import logging
import signal
import sys
from typing import Callable

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Config

logger = logging.getLogger(__name__)


def run_scheduler(config: Config, backup_fn: Callable[[Config], None]) -> None:
    """Run the backup scheduler indefinitely.

    Args:
        config: Application configuration with schedule.
        backup_fn: Function to call for each backup run.
    """
    scheduler = BlockingScheduler()

    trigger = CronTrigger.from_crontab(config.schedule)
    scheduler.add_job(
        lambda: backup_fn(config),
        trigger,
        id="notion_backup",
    )

    def shutdown(signum, frame):
        logger.info("Received shutdown signal, stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info(f"Starting scheduler with schedule: {config.schedule}")
    logger.info("Waiting for next scheduled backup...")

    scheduler.start()

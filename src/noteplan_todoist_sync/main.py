"""Main entry point for NotePlan → Todoist sync."""

from __future__ import annotations

import logging
import sys

from .config import Config, ConfigError
from .noteplan_parser import parse_notes_directory
from .sync_engine import SyncEngine
from .todoist_client import TodoistClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the NotePlan → Todoist sync."""
    try:
        config = Config.from_env()
    except ConfigError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)

    logger.info("Parsing notes from: %s", config.notes_directory)
    tasks = parse_notes_directory(config.notes_directory)
    logger.info("Found %d tasks in NotePlan notes", len(tasks))

    if not tasks:
        logger.info("No tasks found, nothing to sync.")
        return

    open_tasks = [t for t in tasks if not t.completed]
    completed_tasks = [t for t in tasks if t.completed]
    logger.info("  Open: %d | Completed: %d", len(open_tasks), len(completed_tasks))

    client = TodoistClient(
        api_token=config.todoist_api_token,
        project_id=config.todoist_project_id,
    )
    engine = SyncEngine(todoist=client, state_path=config.sync_state_path)

    report = engine.sync(tasks)
    logger.info("Sync report: %s", report)

    if not report.success:
        for err in report.errors:
            logger.error("  %s", err)
        sys.exit(1)


if __name__ == "__main__":
    main()

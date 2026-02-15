"""Sync engine that coordinates changes between NotePlan and Todoist."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .models import SyncState, Task
from .todoist_client import TodoistClient

logger = logging.getLogger(__name__)

STATE_FILE = ".sync_state.json"


class SyncEngine:
    """Orchestrates syncing NotePlan tasks to Todoist."""

    def __init__(self, todoist: TodoistClient, state_path: Path | None = None):
        self.todoist = todoist
        self.state_path = state_path or Path(STATE_FILE)
        self.state = self._load_state()

    def sync(self, noteplan_tasks: list[Task]) -> SyncReport:
        """Sync NotePlan tasks to Todoist.

        For each NotePlan task:
        - If it's new (not in state), create it in Todoist
        - If it exists (in state), update it in Todoist
        - If it's completed, mark it complete in Todoist
        """
        report = SyncReport()

        for task in noteplan_tasks:
            key = task.identity_key
            existing_todoist_id = self.state.task_map.get(key)

            if existing_todoist_id:
                if task.completed:
                    result = self.todoist.complete_task(existing_todoist_id)
                    if result.success:
                        report.completed += 1
                    else:
                        report.errors.append(f"Complete failed: {task.content} - {result.error}")
                else:
                    result = self.todoist.update_task(existing_todoist_id, task)
                    if result.success:
                        report.updated += 1
                    else:
                        report.errors.append(f"Update failed: {task.content} - {result.error}")
            else:
                if task.completed:
                    # Already done, no need to create in Todoist
                    report.skipped += 1
                    continue

                result = self.todoist.create_task(task)
                if result.success and result.todoist_id:
                    self.state.task_map[key] = result.todoist_id
                    report.created += 1
                else:
                    report.errors.append(f"Create failed: {task.content} - {result.error}")

        self.state.last_sync = datetime.now(timezone.utc).isoformat()
        self._save_state()

        logger.info(
            "Sync complete: %d created, %d updated, %d completed, %d skipped, %d errors",
            report.created,
            report.updated,
            report.completed,
            report.skipped,
            len(report.errors),
        )

        return report

    def _load_state(self) -> SyncState:
        """Load sync state from disk."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                return SyncState(
                    task_map=data.get("task_map", {}),
                    last_sync=data.get("last_sync", ""),
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to load sync state, starting fresh: %s", e)
        return SyncState()

    def _save_state(self) -> None:
        """Persist sync state to disk."""
        data = {
            "task_map": self.state.task_map,
            "last_sync": self.state.last_sync,
        }
        self.state_path.write_text(json.dumps(data, indent=2))


class SyncReport:
    """Summary of a sync operation."""

    def __init__(self) -> None:
        self.created: int = 0
        self.updated: int = 0
        self.completed: int = 0
        self.skipped: int = 0
        self.errors: list[str] = []

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        parts = [
            f"Created: {self.created}",
            f"Updated: {self.updated}",
            f"Completed: {self.completed}",
            f"Skipped: {self.skipped}",
        ]
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        return " | ".join(parts)

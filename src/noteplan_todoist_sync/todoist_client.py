"""Client for the Todoist REST API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from requests import HTTPError
from todoist_api_python.api import TodoistAPI

from .models import Priority, Task

logger = logging.getLogger(__name__)

# Seconds to wait between API calls to avoid burst throttling
REQUEST_DELAY = 0.35
# Max retries for 429 (rate-limited) responses
MAX_RETRIES = 3


@dataclass
class TodoistResult:
    """Result of a Todoist API operation."""

    success: bool
    todoist_id: str | None = None
    error: str | None = None


def _http_status(exc: Exception) -> int | None:
    """Extract HTTP status code from an exception, if available."""
    if isinstance(exc, HTTPError) and exc.response is not None:
        return exc.response.status_code
    return None


class TodoistClient:
    """Wrapper around the Todoist API for task sync operations."""

    def __init__(self, api_token: str, project_id: str | None = None):
        self.api = TodoistAPI(api_token)
        self.project_id = project_id
        self._consecutive_forbidden = 0

    def _throttle(self) -> None:
        """Small delay between API calls to avoid burst throttling."""
        time.sleep(REQUEST_DELAY)

    def _call_api(self, fn, *args, **kwargs):
        """Call a Todoist API method with retry on 429."""
        for attempt in range(MAX_RETRIES + 1):
            try:
                self._throttle()
                result = fn(*args, **kwargs)
                self._consecutive_forbidden = 0
                return result
            except Exception as e:
                if _http_status(e) == 429 and attempt < MAX_RETRIES:
                    wait = 2 ** (attempt + 1)
                    logger.warning("Rate limited, retrying in %ds...", wait)
                    time.sleep(wait)
                    continue
                raise

    def get_all_tasks(self) -> list[Task]:
        """Fetch all tasks from Todoist (optionally filtered by project)."""
        try:
            kwargs = {}
            if self.project_id:
                kwargs["project_id"] = self.project_id
            todoist_tasks = self._call_api(self.api.get_tasks, **kwargs)
        except Exception as e:
            logger.error("Failed to fetch tasks from Todoist: %s", e)
            return []

        tasks = []
        for t in todoist_tasks:
            due_date = None
            if t.due and t.due.date:
                from datetime import date

                try:
                    due_date = date.fromisoformat(t.due.date)
                except ValueError:
                    pass

            tasks.append(
                Task(
                    content=t.content,
                    completed=t.is_completed,
                    priority=Priority.from_todoist(t.priority),
                    due_date=due_date,
                    tags=t.labels,
                    todoist_id=t.id,
                )
            )

        return tasks

    def create_task(self, task: Task) -> TodoistResult:
        """Create a new task in Todoist."""
        if self._consecutive_forbidden >= 3:
            return TodoistResult(
                success=False,
                error="Skipped — Todoist returned 403 Forbidden on previous requests "
                "(possible active task limit reached)",
            )

        try:
            kwargs: dict = {
                "content": task.content,
                "priority": task.priority.to_todoist(),
            }

            if self.project_id:
                kwargs["project_id"] = self.project_id

            if task.due_date:
                kwargs["due_date"] = task.due_date

            if task.tags:
                kwargs["labels"] = task.tags

            result = self._call_api(self.api.add_task, **kwargs)
            logger.info("Created task in Todoist: %s (id=%s)", task.content, result.id)
            return TodoistResult(success=True, todoist_id=result.id)

        except Exception as e:
            if _http_status(e) == 403:
                self._consecutive_forbidden += 1
                if self._consecutive_forbidden >= 3:
                    logger.error(
                        "Todoist returned 403 Forbidden 3 times in a row — "
                        "you may have hit your plan's active task limit. "
                        "Skipping remaining creates."
                    )
            logger.error("Failed to create task '%s': %s", task.content, e)
            return TodoistResult(success=False, error=str(e))

    def update_task(self, todoist_id: str, task: Task) -> TodoistResult:
        """Update an existing task in Todoist."""
        try:
            kwargs: dict = {
                "content": task.content,
                "priority": task.priority.to_todoist(),
            }

            if task.due_date:
                kwargs["due_date"] = task.due_date

            if task.tags:
                kwargs["labels"] = task.tags

            self._call_api(self.api.update_task, task_id=todoist_id, **kwargs)
            logger.info("Updated task in Todoist: %s (id=%s)", task.content, todoist_id)
            return TodoistResult(success=True, todoist_id=todoist_id)

        except Exception as e:
            logger.error("Failed to update task '%s': %s", task.content, e)
            return TodoistResult(success=False, error=str(e))

    def complete_task(self, todoist_id: str) -> TodoistResult:
        """Mark a task as complete in Todoist."""
        try:
            self._call_api(self.api.close_task, task_id=todoist_id)
            logger.info("Completed task in Todoist: id=%s", todoist_id)
            return TodoistResult(success=True, todoist_id=todoist_id)

        except Exception as e:
            logger.error("Failed to complete task id=%s: %s", todoist_id, e)
            return TodoistResult(success=False, error=str(e))

"""Tests for the sync engine."""

from pathlib import Path
from unittest.mock import MagicMock

from noteplan_todoist_sync.models import Task
from noteplan_todoist_sync.sync_engine import SyncEngine
from noteplan_todoist_sync.todoist_client import TodoistClient, TodoistResult


def make_task(**kwargs) -> Task:
    """Helper to create a Task with defaults."""
    defaults = {
        "content": "Test task",
        "source_file": "test.md",
        "source_line": 1,
    }
    defaults.update(kwargs)
    return Task(**defaults)


class TestSyncEngine:
    def setup_method(self):
        self.todoist = MagicMock(spec=TodoistClient)
        self.state_path = Path("/tmp/test_sync_state.json")
        if self.state_path.exists():
            self.state_path.unlink()
        self.engine = SyncEngine(todoist=self.todoist, state_path=self.state_path)

    def teardown_method(self):
        if self.state_path.exists():
            self.state_path.unlink()

    def test_creates_new_open_tasks(self):
        self.todoist.create_task.return_value = TodoistResult(
            success=True, todoist_id="todoist-123"
        )

        task = make_task(content="New task")
        report = self.engine.sync([task])

        assert report.created == 1
        self.todoist.create_task.assert_called_once_with(task)

    def test_skips_already_completed_new_tasks(self):
        task = make_task(content="Done task", completed=True)
        report = self.engine.sync([task])

        assert report.skipped == 1
        self.todoist.create_task.assert_not_called()

    def test_updates_existing_tasks(self):
        self.todoist.update_task.return_value = TodoistResult(
            success=True, todoist_id="todoist-123"
        )

        task = make_task(content="Existing task")
        key = task.identity_key
        self.engine.state.task_map[key] = "todoist-123"

        report = self.engine.sync([task])

        assert report.updated == 1
        self.todoist.update_task.assert_called_once_with("todoist-123", task)

    def test_completes_tasks_in_todoist(self):
        self.todoist.complete_task.return_value = TodoistResult(
            success=True, todoist_id="todoist-123"
        )

        task = make_task(content="Now done", completed=True)
        key = task.identity_key
        self.engine.state.task_map[key] = "todoist-123"

        report = self.engine.sync([task])

        assert report.completed == 1
        self.todoist.complete_task.assert_called_once_with("todoist-123")

    def test_persists_state(self):
        self.todoist.create_task.return_value = TodoistResult(
            success=True, todoist_id="todoist-456"
        )

        task = make_task(content="Persist me", source_file="note.md", source_line=3)
        self.engine.sync([task])

        assert self.state_path.exists()

        # Load a new engine and verify it picks up the state
        engine2 = SyncEngine(todoist=self.todoist, state_path=self.state_path)
        assert "note.md:3" in engine2.state.task_map
        assert engine2.state.task_map["note.md:3"] == "todoist-456"

    def test_reports_errors(self):
        self.todoist.create_task.return_value = TodoistResult(
            success=False, error="API error"
        )

        task = make_task(content="Failing task")
        report = self.engine.sync([task])

        assert report.created == 0
        assert len(report.errors) == 1
        assert not report.success

    def test_full_sync_mixed_tasks(self):
        """Test a sync with a mix of new, existing, and completed tasks."""
        self.todoist.create_task.return_value = TodoistResult(
            success=True, todoist_id="new-1"
        )
        self.todoist.update_task.return_value = TodoistResult(
            success=True, todoist_id="existing-1"
        )
        self.todoist.complete_task.return_value = TodoistResult(
            success=True, todoist_id="existing-2"
        )

        new_task = make_task(content="Brand new", source_line=1)
        existing_task = make_task(content="Updated", source_line=2)
        completed_task = make_task(content="All done", source_line=3, completed=True)
        skipped_task = make_task(content="Already done", source_line=4, completed=True)

        self.engine.state.task_map["test.md:2"] = "existing-1"
        self.engine.state.task_map["test.md:3"] = "existing-2"

        report = self.engine.sync([new_task, existing_task, completed_task, skipped_task])

        assert report.created == 1
        assert report.updated == 1
        assert report.completed == 1
        assert report.skipped == 1
        assert report.success

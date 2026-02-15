"""Tests for the NotePlan markdown writer (migration marking)."""

from pathlib import Path

from noteplan_todoist_sync.models import Task
from noteplan_todoist_sync.noteplan_writer import (
    _rewrite_task_line,
    mark_tasks_as_migrated,
)


class TestRewriteTaskLine:
    def test_simple_open_task(self):
        result = _rewrite_task_line("* Buy groceries\n")
        assert result == "* [x] Buy groceries #status/migrated\n"

    def test_task_with_tags_and_metadata(self):
        result = _rewrite_task_line("* Fix bug #dev >2025-03-15 !!\n")
        assert result == "* [x] Fix bug #dev >2025-03-15 !! #status/migrated\n"

    def test_indented_task(self):
        result = _rewrite_task_line("  * Sub-task\n")
        assert result == "  * [x] Sub-task #status/migrated\n"

    def test_already_completed_and_tagged(self):
        line = "* [x] Done task #status/migrated\n"
        result = _rewrite_task_line(line)
        assert result == line  # unchanged

    def test_completed_without_tag(self):
        result = _rewrite_task_line("* [x] Done task\n")
        assert result == "* [x] Done task #status/migrated\n"

    def test_non_task_line_returns_none(self):
        assert _rewrite_task_line("# Heading\n") is None
        assert _rewrite_task_line("Some text\n") is None
        assert _rewrite_task_line("\n") is None

    def test_preserves_crlf_line_endings(self):
        result = _rewrite_task_line("* Task\r\n")
        assert result == "* [x] Task #status/migrated\r\n"

    def test_no_line_ending(self):
        result = _rewrite_task_line("* Task")
        assert result == "* [x] Task #status/migrated"

    def test_task_with_hierarchical_tag(self):
        result = _rewrite_task_line("* Deploy #domain/infra\n")
        assert result == "* [x] Deploy #domain/infra #status/migrated\n"

    def test_open_task_already_has_migrated_tag(self):
        # Edge case: open but already tagged (shouldn't normally happen)
        result = _rewrite_task_line("* Task #status/migrated\n")
        assert result == "* [x] Task #status/migrated\n"


class TestMarkTasksAsMigrated:
    def test_marks_single_task(self, tmp_path: Path):
        note = tmp_path / "daily.md"
        note.write_text("# Today\n* Buy milk\n* Already done\n")

        task = Task(
            content="Buy milk",
            source_file="daily.md",
            source_line=2,
            source_path=note,
        )

        errors = mark_tasks_as_migrated([task], tmp_path)
        assert errors == []
        assert note.read_text() == (
            "# Today\n* [x] Buy milk #status/migrated\n* Already done\n"
        )

    def test_marks_multiple_tasks_same_file(self, tmp_path: Path):
        note = tmp_path / "daily.md"
        note.write_text("# Today\n* Task A\n* Task B\n* Task C\n")

        tasks = [
            Task(
                content="Task A",
                source_file="daily.md",
                source_line=2,
                source_path=note,
            ),
            Task(
                content="Task C",
                source_file="daily.md",
                source_line=4,
                source_path=note,
            ),
        ]

        errors = mark_tasks_as_migrated(tasks, tmp_path)
        assert errors == []

        result = note.read_text()
        assert "* [x] Task A #status/migrated\n" in result
        assert "* Task B\n" in result  # unchanged
        assert "* [x] Task C #status/migrated\n" in result

    def test_marks_tasks_across_files(self, tmp_path: Path):
        note1 = tmp_path / "file1.md"
        note2 = tmp_path / "file2.md"
        note1.write_text("* Task 1\n")
        note2.write_text("* Task 2\n")

        tasks = [
            Task(
                content="Task 1",
                source_file="file1.md",
                source_line=1,
                source_path=note1,
            ),
            Task(
                content="Task 2",
                source_file="file2.md",
                source_line=1,
                source_path=note2,
            ),
        ]

        errors = mark_tasks_as_migrated(tasks, tmp_path)
        assert errors == []
        assert "* [x] Task 1 #status/migrated\n" in note1.read_text()
        assert "* [x] Task 2 #status/migrated\n" in note2.read_text()

    def test_error_when_file_not_found(self, tmp_path: Path):
        task = Task(
            content="Ghost",
            source_file="gone.md",
            source_line=1,
            source_path=tmp_path / "gone.md",
        )
        errors = mark_tasks_as_migrated([task], tmp_path)
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_error_when_line_out_of_range(self, tmp_path: Path):
        note = tmp_path / "short.md"
        note.write_text("* Only one line\n")

        task = Task(
            content="Nonexistent",
            source_file="short.md",
            source_line=99,
            source_path=note,
        )
        errors = mark_tasks_as_migrated([task], tmp_path)
        assert len(errors) == 1
        assert "out of range" in errors[0]

    def test_error_when_no_source_path(self, tmp_path: Path):
        task = Task(content="No path", source_file="x.md", source_line=1)
        errors = mark_tasks_as_migrated([task], tmp_path)
        assert len(errors) == 1
        assert "no source_path" in errors[0]

    def test_preserves_non_task_lines(self, tmp_path: Path):
        note = tmp_path / "mixed.md"
        note.write_text("# Heading\n\nSome text.\n\n* Migrate me\n\nMore text.\n")

        task = Task(
            content="Migrate me",
            source_file="mixed.md",
            source_line=5,
            source_path=note,
        )
        errors = mark_tasks_as_migrated([task], tmp_path)
        assert errors == []

        result = note.read_text()
        assert "# Heading\n" in result
        assert "Some text.\n" in result
        assert "More text.\n" in result
        assert "* [x] Migrate me #status/migrated\n" in result

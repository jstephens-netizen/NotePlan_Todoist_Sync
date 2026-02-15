"""Tests for the NotePlan markdown parser."""

from datetime import date, timedelta
from pathlib import Path
from textwrap import dedent

from noteplan_todoist_sync.models import Priority
from noteplan_todoist_sync.noteplan_parser import parse_file, parse_task_line


class TestParseTaskLine:
    def test_simple_open_task(self):
        task = parse_task_line("- [ ] Buy groceries")
        assert task is not None
        assert task.content == "Buy groceries"
        assert task.completed is False

    def test_completed_task(self):
        task = parse_task_line("- [x] Send email")
        assert task is not None
        assert task.content == "Send email"
        assert task.completed is True

    def test_task_with_tags(self):
        task = parse_task_line("- [ ] Fix bug #dev #urgent")
        assert task is not None
        assert task.content == "Fix bug"
        assert task.tags == ["dev", "urgent"]

    def test_task_with_due_date(self):
        task = parse_task_line("- [ ] Submit report >2025-03-15")
        assert task is not None
        assert task.content == "Submit report"
        assert task.due_date == date(2025, 3, 15)

    def test_task_with_today(self):
        task = parse_task_line("- [ ] Do laundry >today")
        assert task is not None
        assert task.due_date == date.today()

    def test_task_with_tomorrow(self):
        task = parse_task_line("- [ ] Meeting prep >tomorrow")
        assert task is not None
        assert task.due_date == date.today() + timedelta(days=1)

    def test_task_with_low_priority(self):
        task = parse_task_line("- [ ] Low priority task !")
        assert task is not None
        assert task.priority == Priority.LOW

    def test_task_with_medium_priority(self):
        task = parse_task_line("- [ ] Medium priority task !!")
        assert task is not None
        assert task.priority == Priority.MEDIUM

    def test_task_with_high_priority(self):
        task = parse_task_line("- [ ] High priority task !!!")
        assert task is not None
        assert task.priority == Priority.HIGH

    def test_task_with_all_metadata(self):
        task = parse_task_line("- [ ] Review PR #dev #review >2025-01-20 !!")
        assert task is not None
        assert task.content == "Review PR"
        assert task.tags == ["dev", "review"]
        assert task.due_date == date(2025, 1, 20)
        assert task.priority == Priority.MEDIUM
        assert task.completed is False

    def test_non_task_line_returns_none(self):
        assert parse_task_line("# Heading") is None
        assert parse_task_line("Some paragraph text") is None
        assert parse_task_line("") is None
        assert parse_task_line("- Just a list item") is None

    def test_indented_task(self):
        task = parse_task_line("  - [ ] Sub-task")
        assert task is not None
        assert task.content == "Sub-task"

    def test_source_tracking(self):
        task = parse_task_line("- [ ] Track me", source_file="daily.md", line_number=5)
        assert task is not None
        assert task.source_file == "daily.md"
        assert task.source_line == 5
        assert task.identity_key == "daily.md:5"


class TestParseFile:
    def test_parse_file_with_mixed_content(self, tmp_path: Path):
        note = tmp_path / "daily.md"
        note.write_text(dedent("""\
            # Daily Note

            Some thoughts about the day.

            ## Tasks
            - [ ] Buy milk #errands
            - [x] Send invoice #work
            - [ ] Call dentist >2025-02-01 !!

            ## Notes
            More text here.
        """))

        tasks = parse_file(note)
        assert len(tasks) == 3
        assert tasks[0].content == "Buy milk"
        assert tasks[0].tags == ["errands"]
        assert tasks[1].completed is True
        assert tasks[2].due_date == date(2025, 2, 1)
        assert tasks[2].priority == Priority.MEDIUM

    def test_parse_empty_file(self, tmp_path: Path):
        note = tmp_path / "empty.md"
        note.write_text("# Just a heading\n\nNo tasks here.\n")

        tasks = parse_file(note)
        assert tasks == []

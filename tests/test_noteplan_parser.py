"""Tests for the NotePlan markdown parser."""

from datetime import date, timedelta
from pathlib import Path
from textwrap import dedent

from noteplan_todoist_sync.models import Priority
from noteplan_todoist_sync.noteplan_parser import (
    _build_description,
    _noteplan_deep_link,
    parse_file,
    parse_task_line,
)


class TestParseTaskLine:
    def test_simple_open_task(self):
        task = parse_task_line("* Buy groceries")
        assert task is not None
        assert task.content == "Buy groceries"
        assert task.completed is False

    def test_completed_task(self):
        task = parse_task_line("* [x] Send email")
        assert task is not None
        assert task.content == "Send email"
        assert task.completed is True

    def test_completed_task_with_done_marker(self):
        task = parse_task_line(
            "* [x] Send email @done(2026-02-15 12:44 PM)"
        )
        assert task is not None
        assert task.content == "Send email"
        assert task.completed is True

    def test_task_with_tags(self):
        task = parse_task_line("* Fix bug #dev #urgent")
        assert task is not None
        assert task.content == "Fix bug"
        assert task.tags == ["dev", "urgent"]

    def test_task_with_hierarchical_tags(self):
        task = parse_task_line("* Deploy service #domain/infrastructure")
        assert task is not None
        assert task.content == "Deploy service"
        assert task.tags == ["domain/infrastructure"]

    def test_task_with_due_date(self):
        task = parse_task_line("* Submit report >2025-03-15")
        assert task is not None
        assert task.content == "Submit report"
        assert task.due_date == date(2025, 3, 15)

    def test_task_with_today(self):
        task = parse_task_line("* Do laundry >today")
        assert task is not None
        assert task.due_date == date.today()

    def test_task_with_tomorrow(self):
        task = parse_task_line("* Meeting prep >tomorrow")
        assert task is not None
        assert task.due_date == date.today() + timedelta(days=1)

    def test_task_with_low_priority(self):
        task = parse_task_line("* Low priority task !")
        assert task is not None
        assert task.priority == Priority.LOW

    def test_task_with_medium_priority(self):
        task = parse_task_line("* Medium priority task !!")
        assert task is not None
        assert task.priority == Priority.MEDIUM

    def test_task_with_high_priority(self):
        task = parse_task_line("* High priority task !!!")
        assert task is not None
        assert task.priority == Priority.HIGH

    def test_task_with_all_metadata(self):
        task = parse_task_line("* Review PR #dev #review >2025-01-20 !!")
        assert task is not None
        assert task.content == "Review PR"
        assert task.tags == ["dev", "review"]
        assert task.due_date == date(2025, 1, 20)
        assert task.priority == Priority.MEDIUM
        assert task.completed is False

    def test_real_noteplan_open_task(self):
        task = parse_task_line(
            "* This is a test task that is open #domain/monitoring  >2026-02-16"
        )
        assert task is not None
        assert task.content == "This is a test task that is open"
        assert task.tags == ["domain/monitoring"]
        assert task.due_date == date(2026, 2, 16)
        assert task.completed is False

    def test_real_noteplan_completed_task(self):
        line = (
            "* [x] This is a test Task that is completed"
            " #domain/infrastructure >2026-02-16"
            "   @done(2026-02-15 12:44 PM)"
        )
        task = parse_task_line(line)
        assert task is not None
        assert task.content == "This is a test Task that is completed"
        assert task.tags == ["domain/infrastructure"]
        assert task.due_date == date(2026, 2, 16)
        assert task.completed is True

    def test_non_task_line_returns_none(self):
        assert parse_task_line("# Heading") is None
        assert parse_task_line("Some paragraph text") is None
        assert parse_task_line("") is None

    def test_plain_bullet_without_task_content(self):
        # A bare "* " with text IS a task in NotePlan format
        task = parse_task_line("* Just a list item")
        assert task is not None
        assert task.content == "Just a list item"

    def test_indented_task(self):
        task = parse_task_line("  * Sub-task")
        assert task is not None
        assert task.content == "Sub-task"

    def test_source_tracking(self):
        task = parse_task_line("* Track me", source_file="daily.md", line_number=5)
        assert task is not None
        assert task.source_file == "daily.md"
        assert task.source_line == 5
        assert task.identity_key == "daily.md::track me"


    def test_task_with_status_migrated_tag(self):
        task = parse_task_line("* [x] Migrated task #status/migrated")
        assert task is not None
        assert task.content == "Migrated task"
        assert task.completed is True
        assert "status/migrated" in task.tags


class TestParseFile:
    def test_parse_file_with_mixed_content(self, tmp_path: Path):
        note = tmp_path / "daily.md"
        note.write_text(dedent("""\
            # Daily Note

            Some thoughts about the day.

            ## Tasks
            * Buy milk #errands
            * [x] Send invoice #work @done(2025-01-31 09:00 AM)
            * Call dentist >2025-02-01 !!

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

    def test_source_path_set_by_parse_file(self, tmp_path: Path):
        note = tmp_path / "test.md"
        note.write_text("* A task\n")

        tasks = parse_file(note)
        assert len(tasks) == 1
        assert tasks[0].source_path == note

    def test_parse_empty_file(self, tmp_path: Path):
        note = tmp_path / "empty.md"
        note.write_text("# Just a heading\n\nNo tasks here.\n")

        tasks = parse_file(note)
        assert tasks == []

    def test_description_includes_note_title(self, tmp_path: Path):
        note = tmp_path / "sprint.md"
        note.write_text("# Sprint Planning\n\n* Review backlog\n")

        tasks = parse_file(note)
        assert len(tasks) == 1
        assert "From: Sprint Planning" in tasks[0].description

    def test_description_includes_section_heading(self, tmp_path: Path):
        note = tmp_path / "meeting.md"
        note.write_text("# Weekly Standup\n\n## Action Items\n* Follow up with QA\n")

        tasks = parse_file(note)
        assert len(tasks) == 1
        assert "From: Weekly Standup" in tasks[0].description
        assert "Section: Action Items" in tasks[0].description

    def test_description_includes_deep_link(self, tmp_path: Path):
        note = tmp_path / "meeting.md"
        note.write_text("# Weekly Standup\n* Do something\n")

        tasks = parse_file(note)
        assert len(tasks) == 1
        assert "noteplan://x-callback-url/openNote?noteTitle=meeting" in tasks[0].description

    def test_description_uses_filename_when_no_h1(self, tmp_path: Path):
        note = tmp_path / "My Meeting Notes.md"
        note.write_text("## Tasks\n* Call Bob\n")

        tasks = parse_file(note)
        assert len(tasks) == 1
        assert "From: My Meeting Notes" in tasks[0].description

    def test_section_tracks_nearest_heading(self, tmp_path: Path):
        note = tmp_path / "notes.md"
        note.write_text(
            "# Project Notes\n\n"
            "## Design\n* Wireframe review\n\n"
            "## Development\n* Write API endpoint\n"
        )

        tasks = parse_file(note)
        assert len(tasks) == 2
        assert "Section: Design" in tasks[0].description
        assert "Section: Development" in tasks[1].description


class TestNoteplanDeepLink:
    def test_simple_filename(self, tmp_path: Path):
        link = _noteplan_deep_link(tmp_path / "daily.md")
        assert link == "noteplan://x-callback-url/openNote?noteTitle=daily"

    def test_filename_with_spaces(self, tmp_path: Path):
        link = _noteplan_deep_link(tmp_path / "Sprint Planning 2025.md")
        assert "Sprint%20Planning%202025" in link

    def test_filename_with_special_chars(self, tmp_path: Path):
        link = _noteplan_deep_link(tmp_path / "Q&A Session.md")
        assert "Q%26A%20Session" in link


class TestBuildDescription:
    def test_with_title_and_section(self, tmp_path: Path):
        desc = _build_description(tmp_path / "note.md", "My Meeting", "Action Items")
        assert "From: My Meeting" in desc
        assert "Section: Action Items" in desc
        assert "Open in NotePlan" in desc

    def test_without_section(self, tmp_path: Path):
        desc = _build_description(tmp_path / "note.md", "My Meeting", None)
        assert "From: My Meeting" in desc
        assert "Section:" not in desc

    def test_without_title_uses_filename(self, tmp_path: Path):
        desc = _build_description(tmp_path / "daily.md", None, None)
        assert "From: daily" in desc

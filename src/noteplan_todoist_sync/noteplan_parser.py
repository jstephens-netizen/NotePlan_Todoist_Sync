"""Parser for NotePlan markdown files.

NotePlan task format:
    * Open task #tag1 #domain/subtag >2024-01-15 !!
    * [x] Completed task @done(2024-01-15 12:00 PM)

Markers:
    - #tag or #domain/subtag → tag/label (hierarchical tags supported)
    - >YYYY-MM-DD            → due date
    - >today                 → due today
    - >tomorrow              → due tomorrow
    - !                      → low priority
    - !!                     → medium priority
    - !!!                    → high priority
    - @done(...)             → completion timestamp (stripped)
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from .models import Priority, Task

# Regex patterns for NotePlan task elements
# Matches: "* [x] task" (completed) or "* task" (open)
TASK_PATTERN = re.compile(r"^(\s*)\*\s+(?:\[(x)\]\s+)?(.+)$")
TAG_PATTERN = re.compile(r"#([\w/-]+)")
DUE_DATE_PATTERN = re.compile(r">((\d{4}-\d{2}-\d{2})|today|tomorrow)")
PRIORITY_PATTERN = re.compile(r"(?<!\w)(!{1,3})(?!\w|[^\s])")
DONE_PATTERN = re.compile(r"\s*@done\([^)]*\)")


def parse_task_line(line: str, source_file: str = "", line_number: int = 0) -> Task | None:
    """Parse a single line of NotePlan markdown into a Task.

    Returns None if the line is not a task.
    """
    match = TASK_PATTERN.match(line)
    if not match:
        return None

    completed = match.group(2) == "x"
    raw_content = match.group(3)

    # Strip @done(...) suffix
    raw_content = DONE_PATTERN.sub("", raw_content)

    # Extract tags (supports hierarchical like #domain/infrastructure)
    tags = TAG_PATTERN.findall(raw_content)

    # Extract due date
    due_date = _parse_due_date(raw_content)

    # Extract priority
    priority = _parse_priority(raw_content)

    # Clean content: remove metadata markers to get the plain task text
    content = raw_content
    content = TAG_PATTERN.sub("", content)
    content = DUE_DATE_PATTERN.sub("", content)
    content = PRIORITY_PATTERN.sub("", content)
    content = re.sub(r"\s{2,}", " ", content).strip()

    return Task(
        content=content,
        completed=completed,
        priority=priority,
        due_date=due_date,
        tags=tags,
        source_file=source_file,
        source_line=line_number,
    )


def parse_file(file_path: Path) -> list[Task]:
    """Parse all tasks from a NotePlan markdown file."""
    tasks = []
    text = file_path.read_text(encoding="utf-8")
    relative_path = file_path.name

    for line_number, line in enumerate(text.splitlines(), start=1):
        task = parse_task_line(line, source_file=relative_path, line_number=line_number)
        if task is not None:
            task.source_path = file_path
            tasks.append(task)

    return tasks


def parse_notes_directory(notes_dir: Path) -> list[Task]:
    """Parse all tasks from all markdown files in the notes directory."""
    tasks = []
    if not notes_dir.is_dir():
        return tasks

    for md_file in sorted(notes_dir.rglob("*.md")):
        tasks.extend(parse_file(md_file))

    return tasks


def _parse_due_date(text: str) -> date | None:
    """Extract due date from task text."""
    match = DUE_DATE_PATTERN.search(text)
    if not match:
        return None

    value = match.group(1)
    today = date.today()

    if value == "today":
        return today
    if value == "tomorrow":
        return today + timedelta(days=1)

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_priority(text: str) -> Priority:
    """Extract priority from task text."""
    match = PRIORITY_PATTERN.search(text)
    if not match:
        return Priority.NONE
    return Priority.from_noteplan(match.group(1))

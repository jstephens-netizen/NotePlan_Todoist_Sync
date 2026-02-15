"""Write-back modifications to NotePlan markdown files.

After tasks are successfully synced to Todoist, this module marks them
as migrated in the source markdown:
    * Buy groceries  →  * [x] Buy groceries #status/migrated
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from .models import Task

logger = logging.getLogger(__name__)

MIGRATED_TAG = "#status/migrated"

# Same pattern as the parser — matches "* task" or "* [x] task"
TASK_LINE_PATTERN = re.compile(r"^(\s*)\*\s+(?:\[(x)\]\s+)?(.+)$")


def mark_tasks_as_migrated(
    tasks: list[Task],
    notes_dir: Path,
) -> list[str]:
    """Mark successfully synced tasks as migrated in their source files.

    Modifies the source markdown files in-place:
    - Changes ``* content`` to ``* [x] content #status/migrated``

    Args:
        tasks: Tasks that were successfully created in Todoist.
        notes_dir: Root directory of NotePlan notes (for resolving paths).

    Returns:
        List of error messages (empty if all succeeded).
    """
    errors: list[str] = []

    # Group tasks by their source file path
    tasks_by_file: dict[Path, list[Task]] = defaultdict(list)
    for task in tasks:
        if not task.source_path:
            errors.append(
                f"Task '{task.content}' has no source_path, cannot mark as migrated"
            )
            continue
        tasks_by_file[task.source_path].append(task)

    for file_path, file_tasks in tasks_by_file.items():
        file_errors = _mark_file_tasks(file_path, file_tasks)
        errors.extend(file_errors)

    return errors


def _mark_file_tasks(file_path: Path, tasks: list[Task]) -> list[str]:
    """Apply migration marks to tasks within a single file.

    Reads the file, modifies matching lines, writes the file back.
    Tasks are processed bottom-up so line numbers remain stable.
    """
    errors: list[str] = []

    if not file_path.exists():
        return [f"Source file not found: {file_path}"]

    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Sort tasks by line number descending (bottom-up) to preserve indices
    sorted_tasks = sorted(tasks, key=lambda t: t.source_line, reverse=True)

    for task in sorted_tasks:
        line_idx = task.source_line - 1  # 1-based to 0-based

        if line_idx < 0 or line_idx >= len(lines):
            errors.append(
                f"Line {task.source_line} out of range in {file_path} "
                f"for task '{task.content}'"
            )
            continue

        original_line = lines[line_idx]
        modified_line = _rewrite_task_line(original_line)

        if modified_line is None:
            errors.append(
                f"Line {task.source_line} in {file_path} does not match "
                f"expected task pattern for '{task.content}'"
            )
            continue

        lines[line_idx] = modified_line

    file_path.write_text("".join(lines), encoding="utf-8")
    return errors


def _rewrite_task_line(line: str) -> str | None:
    """Rewrite a single task line to mark it as migrated.

    Transforms::

        * task content #tag >date !!
        * [x] task content #tag >date !! #status/migrated

    Returns None if the line does not match the task pattern.
    Returns the line unchanged if already completed and tagged.
    """
    stripped = line.rstrip("\n\r")
    match = TASK_LINE_PATTERN.match(stripped)
    if not match:
        return None

    indent = match.group(1)
    already_completed = match.group(2) == "x"
    content = match.group(3)

    has_migrated_tag = "status/migrated" in re.findall(r"#([\w/-]+)", content)

    # Already completed and tagged — leave it alone
    if already_completed and has_migrated_tag:
        return line

    # Detect line ending
    line_ending = ""
    if line.endswith("\r\n"):
        line_ending = "\r\n"
    elif line.endswith("\n"):
        line_ending = "\n"
    elif line.endswith("\r"):
        line_ending = "\r"

    content = content.rstrip()

    # Append the migrated tag if not already present
    if not has_migrated_tag:
        content = f"{content} {MIGRATED_TAG}"

    return f"{indent}* [x] {content}{line_ending}"

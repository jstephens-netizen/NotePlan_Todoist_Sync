"""Data models for tasks shared between NotePlan and Todoist."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum


class Priority(IntEnum):
    """Task priority levels.

    NotePlan uses ! (low), !! (medium), !!! (high).
    Todoist uses 1 (normal) through 4 (urgent).
    """

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def to_todoist(self) -> int:
        """Convert to Todoist priority (1=normal, 2=low, 3=medium, 4=urgent)."""
        return {
            Priority.NONE: 1,
            Priority.LOW: 2,
            Priority.MEDIUM: 3,
            Priority.HIGH: 4,
        }[self]

    @classmethod
    def from_todoist(cls, todoist_priority: int) -> Priority:
        """Convert from Todoist priority."""
        return {1: cls.NONE, 2: cls.LOW, 3: cls.MEDIUM, 4: cls.HIGH}.get(
            todoist_priority, cls.NONE
        )

    @classmethod
    def from_noteplan(cls, marker: str) -> Priority:
        """Convert from NotePlan priority markers (!, !!, !!!)."""
        count = len(marker.strip())
        return {1: cls.LOW, 2: cls.MEDIUM, 3: cls.HIGH}.get(count, cls.NONE)


@dataclass
class Task:
    """A task that can be represented in both NotePlan and Todoist."""

    content: str
    completed: bool = False
    priority: Priority = Priority.NONE
    due_date: date | None = None
    tags: list[str] = field(default_factory=list)
    # Tracks where this task lives
    source_file: str = ""
    source_line: int = 0
    todoist_id: str | None = None

    @property
    def identity_key(self) -> str:
        """A stable key for matching tasks across syncs.

        Uses the source file and line as the primary identity,
        falling back to content-based matching.
        """
        if self.source_file and self.source_line:
            return f"{self.source_file}:{self.source_line}"
        return self.content.strip().lower()


@dataclass
class SyncState:
    """Tracks the mapping between NotePlan tasks and Todoist tasks."""

    # Maps noteplan identity_key -> todoist task ID
    task_map: dict[str, str] = field(default_factory=dict)
    # Last sync timestamp (ISO format)
    last_sync: str = ""

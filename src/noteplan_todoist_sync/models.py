"""Data models for tasks shared between NotePlan and Todoist."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from pathlib import Path


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
    description: str = ""
    # Tracks where this task lives
    source_file: str = ""
    source_line: int = 0
    todoist_id: str | None = None
    source_path: Path | None = None

    @property
    def identity_key(self) -> str:
        """A stable key for matching tasks across syncs.

        Uses source file + content so the key survives line-number
        changes when tasks are added/removed above.
        """
        base = self.content.strip().lower()
        if self.source_file:
            return f"{self.source_file}::{base}"
        return base

    @property
    def fingerprint(self) -> str:
        """Content fingerprint for change detection.

        Captures everything that would be sent to Todoist so we can
        skip update calls when nothing has changed.
        """
        due = self.due_date.isoformat() if self.due_date else ""
        tags = ",".join(sorted(self.tags))
        return f"{self.content}|{self.completed}|{self.priority}|{due}|{tags}|{self.description}"


@dataclass
class SyncState:
    """Tracks the mapping between NotePlan tasks and Todoist tasks."""

    # Maps noteplan identity_key -> todoist task ID
    task_map: dict[str, str] = field(default_factory=dict)
    # Maps noteplan identity_key -> fingerprint from last sync
    fingerprints: dict[str, str] = field(default_factory=dict)
    # Last sync timestamp (ISO format)
    last_sync: str = ""

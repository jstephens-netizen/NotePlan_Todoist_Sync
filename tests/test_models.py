"""Tests for data models."""

from noteplan_todoist_sync.models import Priority


class TestPriority:
    def test_to_todoist_mapping(self):
        assert Priority.NONE.to_todoist() == 1
        assert Priority.LOW.to_todoist() == 2
        assert Priority.MEDIUM.to_todoist() == 3
        assert Priority.HIGH.to_todoist() == 4

    def test_from_todoist_mapping(self):
        assert Priority.from_todoist(1) == Priority.NONE
        assert Priority.from_todoist(2) == Priority.LOW
        assert Priority.from_todoist(3) == Priority.MEDIUM
        assert Priority.from_todoist(4) == Priority.HIGH
        assert Priority.from_todoist(99) == Priority.NONE

    def test_from_noteplan_markers(self):
        assert Priority.from_noteplan("!") == Priority.LOW
        assert Priority.from_noteplan("!!") == Priority.MEDIUM
        assert Priority.from_noteplan("!!!") == Priority.HIGH

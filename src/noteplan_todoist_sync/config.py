"""Configuration management via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """Raised when required configuration is missing."""


@dataclass
class Config:
    """Application configuration."""

    todoist_api_token: str
    notes_directory: Path
    todoist_project_id: str | None = None
    sync_state_path: Path = Path(".sync_state.json")

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables.

        Required:
            TODOIST_API_TOKEN: Your Todoist API token

        Optional:
            NOTES_DIR: Path to notes directory (default: ./notes)
            TODOIST_PROJECT_ID: Todoist project to sync to (default: Inbox)
            SYNC_STATE_PATH: Path to sync state file (default: .sync_state.json)
        """
        token = os.environ.get("TODOIST_API_TOKEN")
        if not token:
            raise ConfigError(
                "TODOIST_API_TOKEN environment variable is required. "
                "Get your token from https://todoist.com/app/settings/integrations/developer"
            )

        notes_dir = Path(os.environ.get("NOTES_DIR", "notes"))
        project_id = os.environ.get("TODOIST_PROJECT_ID")
        state_path = Path(os.environ.get("SYNC_STATE_PATH", ".sync_state.json"))

        return cls(
            todoist_api_token=token,
            notes_directory=notes_dir,
            todoist_project_id=project_id,
            sync_state_path=state_path,
        )

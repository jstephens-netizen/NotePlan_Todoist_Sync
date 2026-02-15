# CLAUDE.md

## Project Overview
NotePlan → Todoist sync tool. Parses NotePlan markdown files from the `notes/` directory and syncs tasks to Todoist via GitHub Actions.

## Commands
- `pip install -e ".[dev]"` — install with dev deps
- `pytest` — run tests
- `ruff check src/ tests/` — lint
- `python -m noteplan_todoist_sync.main` — run sync (needs TODOIST_API_TOKEN env var)

## Architecture
- `src/noteplan_todoist_sync/` — main package
  - `models.py` — Task, Priority, SyncState dataclasses
  - `noteplan_parser.py` — parses NotePlan markdown → Task objects
  - `todoist_client.py` — wraps todoist-api-python SDK
  - `sync_engine.py` — orchestrates sync, manages state in `.sync_state.json`
  - `config.py` — loads config from environment variables
  - `main.py` — entry point
- `notes/` — NotePlan markdown files live here
- `.github/workflows/sync.yml` — runs sync on push to main + every 15 min
- `.github/workflows/test.yml` — CI: lint + tests

## Conventions
- Python 3.11+, type hints throughout
- Tests in `tests/`, using pytest
- Ruff for linting
- Config via environment variables (TODOIST_API_TOKEN, TODOIST_PROJECT_ID, NOTES_DIR)

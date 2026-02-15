# CLAUDE.md

## Project Overview
NotePlan → Todoist sync tool. Parses NotePlan markdown files from the `notes/` directory and syncs tasks to Todoist via GitHub Actions. After successful sync, tasks are marked as `* [x] ... #status/migrated` in the source files and committed back.

## Commands
- `pip install -e ".[dev]"` — install with dev deps
- `pytest` — run tests
- `ruff check src/ tests/` — lint
- `python -m noteplan_todoist_sync.main` — run sync (needs TODOIST_API_TOKEN env var)

## Architecture
- `src/noteplan_todoist_sync/` — main package
  - `models.py` — Task, Priority, SyncState dataclasses
  - `noteplan_parser.py` — parses NotePlan markdown → Task objects
  - `noteplan_writer.py` — marks synced tasks as `* [x] ... #status/migrated` in source files
  - `todoist_client.py` — wraps todoist-api-python SDK
  - `sync_engine.py` — orchestrates sync, manages state in `.sync_state.json`
  - `config.py` — loads config from environment variables
  - `main.py` — entry point
- `notes/` — NotePlan markdown files live here
- `.github/workflows/sync.yml` — runs sync on push to main + hourly, commits migration marks back
- `.github/workflows/test.yml` — CI: lint + tests

## Conventions
- Python 3.11+, type hints throughout
- Tests in `tests/`, using pytest
- Ruff for linting
- Config via environment variables (TODOIST_API_TOKEN, TODOIST_PROJECT_ID, NOTES_DIR)

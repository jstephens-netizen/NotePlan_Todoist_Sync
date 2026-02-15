# NotePlan → Todoist Sync

Sync tasks from NotePlan markdown files (stored in this GitHub repo) to Todoist, powered by GitHub Actions.

## How It Works

1. You write notes in the `notes/` directory using NotePlan's markdown task format
2. On push (or every 15 minutes), a GitHub Action parses your notes and syncs tasks to Todoist
3. New tasks are created, existing tasks are updated, and completed tasks are closed in Todoist

## Task Format

```markdown
- [ ] Task description #tag1 #tag2 >2025-03-15 !!
- [x] Completed task
```

| Marker | Meaning | Todoist Mapping |
|--------|---------|-----------------|
| `- [ ]` | Open task | Creates/updates task |
| `- [x]` | Completed task | Closes task |
| `#tag` | Tag/label | Todoist label |
| `>YYYY-MM-DD` | Due date | Due date |
| `>today` | Due today | Due date |
| `>tomorrow` | Due tomorrow | Due date |
| `!` | Low priority | Priority 2 |
| `!!` | Medium priority | Priority 3 |
| `!!!` | High priority | Priority 4 (urgent) |

## Setup

### 1. Get your Todoist API token

Go to [Todoist Settings → Integrations → Developer](https://todoist.com/app/settings/integrations/developer) and copy your API token.

### 2. Add repository secrets

In your GitHub repo, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Required | Description |
|--------|----------|-------------|
| `TODOIST_API_TOKEN` | Yes | Your Todoist API token |
| `TODOIST_PROJECT_ID` | No | Target Todoist project ID (defaults to Inbox) |

### 3. Add your notes

Create markdown files in the `notes/` directory with tasks in the format above. Push to `main` to trigger a sync.

## Local Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Run sync locally
export TODOIST_API_TOKEN="your-token-here"
python -m noteplan_todoist_sync.main
```

## Project Structure

```
├── .github/workflows/
│   ├── sync.yml          # Sync workflow (runs on push + schedule)
│   └── test.yml          # CI workflow (runs tests + lint)
├── src/noteplan_todoist_sync/
│   ├── config.py         # Environment-based configuration
│   ├── main.py           # Entry point
│   ├── models.py         # Shared data models (Task, Priority)
│   ├── noteplan_parser.py # NotePlan markdown parser
│   ├── sync_engine.py    # Sync orchestration + state tracking
│   └── todoist_client.py # Todoist API wrapper
├── tests/                # Test suite
├── notes/                # Your NotePlan markdown files go here
└── pyproject.toml        # Python project config
```

## Roadmap

- [x] NotePlan → Todoist sync (one-way)
- [ ] Bidirectional sync (Todoist → NotePlan)
- [ ] Support for sub-tasks
- [ ] Support for NotePlan scheduling (`<YYYY-MM-DD`)

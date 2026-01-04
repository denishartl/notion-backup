# Notion Backup - Implementation Plan

## Phase 1: Project Skeleton & Config

### Deliverables
- Project structure with `pyproject.toml`
- Config loading and validation (`config.yaml` → Python dataclass)
- Basic CLI entry points (`serve`, `run`)
- Dockerfile that builds and runs

### Files
```
notion-backup/
├── src/
│   └── notion_backup/
│       ├── __init__.py
│       ├── __main__.py      # CLI entry point
│       ├── config.py        # Config loading/validation
│       └── scheduler.py     # Cron scheduling
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── example-config.yaml
```

### Testable
Container starts, reads config, logs "waiting for next scheduled backup"

---

## Phase 2: Notion API Integration

### Deliverables
- Fetch all pages and databases via search API
- Fetch page properties and block content recursively
- Fetch database schema and rows
- Rate limiting handled

### Files
```
src/notion_backup/
├── notion/
│   ├── __init__.py
│   ├── client.py       # Notion API wrapper
│   ├── pages.py        # Page fetching logic
│   └── databases.py    # Database fetching logic
```

### Testable
Run manually, see JSON output of Notion content in logs

---

## Phase 3: Backup Storage (JSON)

### Deliverables
- Create timestamped backup directories
- Save pages and databases as JSON files
- Download and store embedded files
- Generate `manifest.json`

### Files
```
src/notion_backup/
├── backup/
│   ├── __init__.py
│   ├── storage.py      # Directory/file management
│   ├── files.py        # File download logic
│   └── manifest.py     # Manifest generation
```

### Testable
Run backup, see JSON files and downloaded images in `/data/backups/`

---

## Phase 4: Markdown Conversion

### Deliverables
- Convert Notion blocks to Markdown
- Generate frontmatter with metadata
- Create directory hierarchy matching page nesting
- Link to downloaded files

### Files
```
src/notion_backup/
├── markdown/
│   ├── __init__.py
│   ├── converter.py    # Block → Markdown
│   └── writer.py       # File/directory output
```

### Testable
Run backup, see readable Markdown files alongside JSON

---

## Phase 5: Retention & Notifications

### Deliverables
- Delete old backups beyond `retention_count`
- Send Discord webhook on completion/error
- Configurable notification mode

### Files
```
src/notion_backup/
├── retention.py        # Backup pruning
└── notifications.py    # Discord webhook
```

### Testable
Run multiple backups, old ones get deleted, Discord receives message

---

## Phase 6: Polish & Documentation

### Deliverables
- Logging to file (rotating)
- Graceful shutdown handling
- README with setup instructions
- Example config with comments

---

## Dependencies

```
notion-client    # Official Notion SDK
pyyaml           # Config parsing
apscheduler      # Cron scheduling
requests         # Discord webhooks, file downloads
```

## Development Commands

```bash
# Local development
cd /Users/hartlden/private/notion-backup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run locally
python -m notion_backup serve
python -m notion_backup run

# Build Docker image
docker build -t notion-backup .

# Run in Docker
docker compose up -d
docker logs -f notion-backup
docker exec notion-backup python -m notion_backup run
```

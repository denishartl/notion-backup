# Notion Backup - Design Specification

## Overview

A Docker container that creates regular backups of Notion workspaces, designed to run on a Raspberry Pi with Portainer.

## Goals

- **Disaster recovery**: Restore Notion workspace if something catastrophic happens
- **Data portability**: Offline/exportable copy readable without Notion

## Architecture

- **Runtime**: Python 3.11 in Docker container (ARM-compatible)
- **Operation**: Long-running service with cron-based scheduling
- **Storage**: Single mounted volume at `/data`

### Volume Structure

```
/data/
├── config.yaml          # Configuration file
├── backups/             # Backup data organized by workspace
│   ├── personal/
│   │   ├── 2024-01-15_030000/
│   │   └── ...
│   └── work/
│       └── ...
└── logs/                # Rotating log files
    └── backup.log
```

## Configuration

File: `/data/config.yaml`

```yaml
# Backup schedule (cron syntax)
schedule: "0 3 * * *"  # Daily at 3 AM

# How many backups to keep per workspace
retention_count: 7

# Discord notifications
notifications:
  discord_webhook_url: "https://discord.com/api/webhooks/..."
  notify_on: "always"  # "always" = every backup, "error" = only on failure

# Workspaces to back up
workspaces:
  - name: personal
    token_env: NOTION_TOKEN_PERSONAL  # References environment variable

  - name: work
    token_env: NOTION_TOKEN_WORK
```

### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `schedule` | string | Yes | Cron expression (5-field) |
| `retention_count` | integer | Yes | Number of backups to keep per workspace |
| `notifications.discord_webhook_url` | string | No | Discord webhook URL |
| `notifications.notify_on` | string | No | `"always"` or `"error"` (default: `"error"`) |
| `workspaces` | list | Yes | List of workspace configurations |
| `workspaces[].name` | string | Yes | Workspace identifier (used for directory name) |
| `workspaces[].token_env` | string | Yes | Environment variable name containing Notion token |

## Backup Output

### Directory Structure

Each backup creates a timestamped directory:

```
/data/backups/{workspace}/{timestamp}/
├── json/
│   ├── pages/
│   │   ├── {page-id}.json
│   │   └── ...
│   └── databases/
│       ├── {db-id}.json      # Schema + all rows
│       └── ...
├── markdown/
│   ├── Page Title.md
│   ├── Nested Page/
│   │   └── Child Page.md
│   └── ...
├── files/
│   ├── {hash}-filename.png
│   └── ...
└── manifest.json
```

### JSON Format

- Pages: Full Notion API response including properties and all blocks
- Databases: Schema definition plus all rows (as pages)
- Preserves exact Notion data structure for potential restore

### Markdown Format

- Human-readable conversion of Notion content
- YAML frontmatter with metadata (notion_id, timestamps, properties)
- Directory hierarchy mirrors page nesting
- Embedded files referenced with local paths

### Manifest

```json
{
  "timestamp": "2024-01-15T03:00:00Z",
  "duration_seconds": 245,
  "pages_backed_up": 142,
  "databases_backed_up": 8,
  "files_downloaded": 57,
  "errors": [],
  "status": "completed"
}
```

Status values: `"completed"`, `"completed_with_warnings"`, `"failed"`

## Notion API Integration

### Authentication

- Uses Notion Internal Integration tokens
- Created at https://www.notion.so/my-integrations
- Integration must be manually shared with pages/databases to access them

### API Operations

1. `POST /v1/search` - List all accessible pages and databases
2. `GET /v1/pages/{id}` - Fetch page properties
3. `GET /v1/blocks/{id}/children` - Fetch page content (recursive)
4. `GET /v1/databases/{id}` - Fetch database schema
5. `POST /v1/databases/{id}/query` - Fetch all database rows

### Rate Limiting

- Notion API: ~3 requests/second
- SDK handles automatic backoff
- Large workspaces may take several minutes

## Markdown Conversion

### Block Mapping

| Notion Block | Markdown |
|--------------|----------|
| Paragraph | Plain text |
| Heading 1-3 | `#`, `##`, `###` |
| Bulleted list | `- ` |
| Numbered list | `1. ` |
| To-do | `- [ ]` / `- [x]` |
| Code | Fenced code block |
| Quote | `>` |
| Divider | `---` |
| Image | `![alt](files/{hash}-name.png)` |
| Table | Markdown table |
| Callout | Blockquote with emoji |
| Toggle | Header or details/summary HTML |

### Frontmatter

```yaml
---
notion_id: "abc123..."
last_edited: "2024-01-15T10:30:00Z"
created: "2024-01-01T08:00:00Z"
properties:
  Status: "In Progress"
  Tags: ["work", "urgent"]
---
```

## Error Handling

### Philosophy

- Single failed page/file does not abort entire backup
- Collect errors, continue, report at end
- Only fatal errors (bad config, invalid token) stop backup

### Error Categories

| Category | Behavior |
|----------|----------|
| Config invalid | Container fails to start |
| Token invalid | Skip workspace, log, notify |
| Page fetch fails | Log, skip page, continue |
| File download fails | Log, record in manifest, continue |
| Rate limit | Automatic backoff (SDK) |
| Network timeout | Retry 3x, then skip |

### Logging

- stdout (for `docker logs`)
- `/data/logs/backup.log` (rotating, 5 files, 10MB each)
- Levels: INFO (normal), WARNING (skipped), ERROR (failures)

## Notifications

Discord webhook with configurable behavior:

- `notify_on: "error"` - Only send on failures
- `notify_on: "always"` - Send after every backup with summary

Summary includes: workspace, pages/databases backed up, files downloaded, duration, warnings.

## Docker Deployment

### Image

- Base: `python:3.11-slim` (ARM-compatible)
- Runs as non-root user
- Minimal dependencies

### Commands

| Command | Description |
|---------|-------------|
| `serve` (default) | Run scheduler, wait for cron |
| `run` | Immediate backup of all workspaces |
| `run --workspace NAME` | Backup single workspace |

### Docker Compose

```yaml
version: "3.8"
services:
  notion-backup:
    image: notion-backup:latest
    container_name: notion-backup
    restart: unless-stopped
    environment:
      - NOTION_TOKEN_PERSONAL=${NOTION_TOKEN_PERSONAL}
      - NOTION_TOKEN_WORK=${NOTION_TOKEN_WORK}
      - TZ=Europe/Berlin
    volumes:
      - ./notion-backup-data:/data
```

### Manual Trigger

```bash
docker exec notion-backup python -m notion_backup run
```

## Out of Scope (v1)

- Restore functionality
- Web UI
- Incremental backups
- Per-workspace schedules

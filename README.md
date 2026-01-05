# notion-backup

Automated backups for Notion workspaces. Creates scheduled backups of all your Notion content with both JSON (for restore) and Markdown (for reading) formats.

## Features

- **Scheduled backups** via cron syntax
- **Multiple workspaces** with separate Notion tokens
- **JSON export** preserves exact Notion data structure
- **Markdown export** with human-readable content
- **File downloads** for images and attachments
- **Automatic retention** deletes old backups
- **Discord notifications** on success or failure
- **Docker-ready** for Raspberry Pi and other ARM devices

## Installation

Pull the pre-built image from GitHub Container Registry:

```bash
docker pull ghcr.io/denishartl/notion-backup:latest
```

Or pin to a specific version:

```bash
docker pull ghcr.io/denishartl/notion-backup:2025.01.05
```

## Quick Start

### 1. Create a Notion Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Name it (e.g., "Backup Service")
4. Select the workspace to back up
5. Copy the "Internal Integration Token" (starts with `ntn_`)

### 2. Share Pages with the Integration

In Notion, for each page/database you want to back up:
1. Open the page
2. Click "..." menu → "Add connections"
3. Select your integration

**Note:** Child pages inherit access, so sharing a top-level page shares all nested content.

### 3. Configure the Backup

Create a `data/config.yaml` file:

```yaml
# Backup schedule (cron syntax: minute hour day month weekday)
schedule: "0 3 * * *"  # Daily at 3 AM

# Number of backups to keep per workspace
retention_count: 7

# Discord notifications (optional)
notifications:
  discord_webhook_url: "https://discord.com/api/webhooks/..."
  notify_on: "always"  # "always" or "error"

# Workspaces to back up
workspaces:
  - name: personal
    token_env: NOTION_TOKEN_PERSONAL
```

### 4. Run with Docker

```bash
# Set your Notion token
export NOTION_TOKEN_PERSONAL="ntn_your_token_here"

# Start the service
docker compose up -d

# View logs
docker logs -f notion-backup
```

### 5. Manual Backup

To run a backup immediately:

```bash
docker exec notion-backup python -m notion_backup run
```

## Configuration Reference

| Option | Required | Description |
|--------|----------|-------------|
| `schedule` | Yes | Cron expression (5-field) for backup timing |
| `retention_count` | Yes | Number of backups to keep per workspace |
| `notifications.discord_webhook_url` | No | Discord webhook for notifications |
| `notifications.notify_on` | No | `"always"` or `"error"` (default: `"error"`) |
| `workspaces` | Yes | List of workspaces to back up |
| `workspaces[].name` | Yes | Identifier for the workspace |
| `workspaces[].token_env` | Yes | Environment variable containing the Notion token |

## Backup Output

Each backup creates a timestamped directory with:

```
data/backups/{workspace}/{timestamp}/
├── json/
│   ├── pages/{page-id}.json       # Full Notion API data
│   └── databases/{db-id}.json     # Schema + all rows
├── markdown/
│   ├── Page Title.md              # Human-readable content
│   └── Nested Page/
│       └── Child Page.md
├── files/
│   └── {hash}-filename.png        # Downloaded images/files
└── manifest.json                  # Backup summary
```

### Manifest Format

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

Status values: `completed`, `completed_with_warnings`, `failed`

## Docker Compose

```yaml
services:
  notion-backup:
    image: ghcr.io/denishartl/notion-backup:latest
    container_name: notion-backup
    restart: unless-stopped
    environment:
      - NOTION_TOKEN_PERSONAL=${NOTION_TOKEN_PERSONAL}
      - TZ=Europe/Berlin
    volumes:
      - ./data:/data
```

## Commands

| Command | Description |
|---------|-------------|
| `serve` | Run scheduler, wait for cron triggers (default) |
| `run` | Immediate backup of all workspaces |
| `run --workspace NAME` | Backup single workspace |

## Logs

Logs are written to:
- **stdout** for `docker logs`
- **`/data/logs/backup.log`** with rotation (10MB, 5 files)

## Development

For normal usage, use the pre-built image from GHCR. Building locally is only needed for development.

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run locally
python -m notion_backup -c ./data/config.yaml run
```

## Requirements

- Python 3.11+
- Docker (for containerized deployment)
- Notion Internal Integration token

## License

MIT

# notion-backup Monitoring Reference

Source of truth for building Grafana dashboards, Prometheus alerts, and Loki log queries for notion-backup.

---

## Metrics endpoint

| Environment | URL |
|-------------|-----|
| Homelab (Docker) | `http://notion-backup:9101/metrics` |
| Local development | `http://localhost:9101/metrics` |

The endpoint is on the homelab `monitor` network. Prometheus job name: `notion-backup`. See `deploy/homelab/prometheus-scrape.yaml` for the scrape config.

On startup the service **seeds the gauges from each workspace's latest backup manifest**, so `notion_backup_*` gauge series are present immediately after a (re)start rather than only after the next scheduled run. A workspace that has never produced a backup yet exposes no series until its first run. Counters (`notion_backup_runs_total`, `notion_backup_errors_total`) are **not** seeded — they legitimately reset on restart and are read with `increase(...)` in dashboards.

---

## Metric reference

| Metric | Type | Labels | Unit | Meaning |
|--------|------|--------|------|---------|
| `notion_backup_last_success_timestamp_seconds` | Gauge | `workspace` | seconds (Unix) | Timestamp of the last run that did not have status `failed`. Only updated on `completed` or `completed_with_warnings`. |
| `notion_backup_last_run_timestamp_seconds` | Gauge | `workspace` | seconds (Unix) | Timestamp of the most recent run regardless of status. |
| `notion_backup_last_run_status` | Gauge | `workspace` | — | Numeric status of the last run: `0`=completed, `1`=completed_with_warnings, `2`=failed. |
| `notion_backup_runs_total` | Counter | `workspace`, `status` | — | Cumulative run count, broken down by workspace and status string (`completed`, `completed_with_warnings`, `failed`). |
| `notion_backup_last_run_duration_seconds` | Gauge | `workspace` | seconds | Wall-clock duration of the last run. |
| `notion_backup_last_run_phase_duration_seconds` | Gauge | `workspace`, `phase` | seconds | Duration of each phase in the last run. Known phase values: `discover`, `pages`, `databases`, `data_sources`, `files`, `markdown`. |
| `notion_backup_last_run_pages` | Gauge | `workspace` | count | Pages backed up in the last run. |
| `notion_backup_last_run_databases` | Gauge | `workspace` | count | Databases backed up in the last run. |
| `notion_backup_last_run_files` | Gauge | `workspace` | count | Files (images/attachments) downloaded in the last run. |
| `notion_backup_last_run_file_bytes` | Gauge | `workspace` | bytes | Total bytes of files downloaded in the last run. |
| `notion_backup_last_run_errors` | Gauge | `workspace` | count | Error count in the last run (snapshot; does not accumulate across runs). |
| `notion_backup_errors_total` | Counter | `workspace`, `type` | — | Cumulative error count by type. Known type values: `page`, `database`, `data_source`, `file`, `backup`. |

### `_created` series

`prometheus_client` automatically emits a companion `*_created` gauge for every Counter family, recording when the counter was initialised. These appear in the `/metrics` output as:

- `notion_backup_runs_created`
- `notion_backup_errors_created`

They carry the same labels as their parent counter and are managed by the client library — no action needed.

Note: `notion_backup_errors_total` and `notion_backup_errors_created` only appear after the first error of a given `type` is recorded. An absence of those series means no errors have occurred yet; the gauges, by contrast, appear after the first run regardless.

### Standard process/Python metrics

The default `prometheus_client` registry also exposes `process_*` (CPU, memory, file descriptors) and `python_*` (GC stats) families. These are standard and not documented here.

---

## PromQL for dashboard panels

All examples assume Prometheus job `notion-backup`. Replace `workspace="personal"` with a variable or remove the filter for multi-workspace views.

### Backup freshness

```promql
# Hours since last successful backup (lower is better; alert fires at >36h)
(time() - notion_backup_last_success_timestamp_seconds) / 3600
```

### Last-run status

```promql
# 0=completed, 1=completed_with_warnings, 2=failed
notion_backup_last_run_status
```

### Run counts over 7 days

```promql
# Successful runs
increase(notion_backup_runs_total{status="completed"}[7d])

# Per-status breakdown (use as separate queries or stack by status label)
increase(notion_backup_runs_total[7d])
```

### Items backed up (gauges, last run)

```promql
notion_backup_last_run_pages
notion_backup_last_run_databases
notion_backup_last_run_files
```

### File storage downloaded

```promql
# Bytes in last run
notion_backup_last_run_file_bytes

# Convert to MiB for display
notion_backup_last_run_file_bytes / 1024 / 1024
```

### Error breakdown

```promql
# Cumulative totals by type
notion_backup_errors_total

# Errors in the last day (rate of new errors)
increase(notion_backup_errors_total[1d])

# Total error count in last run
notion_backup_last_run_errors
```

### Run duration

```promql
# Total wall-clock duration in seconds
notion_backup_last_run_duration_seconds

# Per-phase breakdown (facet by phase label)
notion_backup_last_run_phase_duration_seconds
```

---

## Logs (Loki)

The app writes structured JSON to stdout. Docker/Alloy collects container stdout and applies the following labels:

| Label | Value |
|-------|-------|
| `container` | `backup-notion-backup-1` (Compose `<project>-<service>-<index>`; the deployed stack does not set `container_name`) |
| `stack_name` | `backup` |
| `job` | `docker_logs` |

### JSON fields emitted per log line

| Field | Description |
|-------|-------------|
| `timestamp` | ISO-8601 timestamp |
| `level` | Log level string (`debug`, `info`, `warning`, `error`, `critical`) |
| `msg` | Log message |
| `logger` | Logger name (Python module path) |

### Example LogQL

```logql
# All logs from notion-backup
{stack_name="backup", container="backup-notion-backup-1"} | json

# Error and critical lines only
{stack_name="backup", container="backup-notion-backup-1"} | json | level=~"error|critical"

# Count error lines in last 15 minutes (used by the log-errors alert)
sum(count_over_time({stack_name="backup", container="backup-notion-backup-1"} | json | level=~"error|critical" [15m]))
```

Note: per-item failures (a page/database/file that could not be fetched) are logged at
`warning` level and end the run as `completed_with_warnings`. They are **not** matched by
the `error|critical` selector — the `notion-backup-warnings` metric alert covers those.

---

## Alerts

Alert rules are provisioned from [`deploy/homelab/grafana-notion-backup-alerts.yaml`](deploy/homelab/grafana-notion-backup-alerts.yaml). Four rules are defined:

| Rule UID | Title | Signal | Threshold |
|----------|-------|--------|-----------|
| `notion-backup-stale` | Notion backup stale | `notion_backup_last_success_timestamp_seconds` — fires when `time() - last_success > 129600s` (36 h) | severity: critical |
| `notion-backup-failed` | Notion backup failed | `notion_backup_last_run_status` — fires when status `> 1.5` (i.e. value `2` = failed) | severity: critical |
| `notion-backup-warnings` | Notion backup completed with warnings | `notion_backup_last_run_status` — fires when status is within `[0.5, 1.5]` (i.e. value `1` = completed_with_warnings) | severity: warning |
| `notion-backup-log-errors` | Notion backup log errors | Loki `count_over_time` of `level=~"error\|critical"` over 15 m for `container="backup-notion-backup-1"` — fires when count `> 0` | severity: warning |

All use `noDataState: OK`. The metric-based rules stay reliable across restarts because the gauges are seeded from disk at startup (see § Metrics endpoint).

Routing is handled by the existing Grafana notification policy (alerts go to the configured contact point — no per-rule routing needed).

> **Note on Loki datasource UID**: the `notion-backup-log-errors` rule uses `datasourceUid: loki`. This requires the Loki datasource in your Grafana provisioning to have `uid: loki` set explicitly. See the comment at the top of the alerts file for details.

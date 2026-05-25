# notion-backup homelab deployment

Steps to wire notion-backup into the homelab `backup` stack.

## Prerequisites

- Access to the `denishartl/homelab` repo
- Portainer access to the `backup` and `monitor` stacks

---

## Steps

### 1. Merge the service into `stacks/backup/docker-compose.yaml`

Open `backup-stack-service.yaml` and copy:

- The `notion-backup` block into the existing `services:` section.
- The `notion-backup-data:` entry into the existing `volumes:` section.
- The `networks.monitor` block is already declared in the backup stack — no change needed there.

### 2. Commit the app config to `stacks/backup/config/`

Copy `notion-backup.yaml` to `stacks/backup/config/notion-backup.yaml` and commit it.

This file is mounted read-only into the container at `/data/config.yaml`.

### 3. Set `NOTION_TOKEN_PERSONAL` in Portainer

In Portainer, open the `backup` stack environment variables and add:

```
NOTION_TOKEN_PERSONAL=<your Notion integration token>
```

Create the token at https://www.notion.so/my-integrations.

### 4. Append the Prometheus scrape job

Append the contents of `prometheus-scrape.yaml` under the `scrape_configs:` list in
`stacks/monitor/config/prometheus.yaml`, then redeploy the `monitor` stack to reload
Prometheus config.

### 5. Add the Grafana alert rules

Copy `grafana-notion-backup-alerts.yaml` to
`stacks/monitor/grafana/alerting/grafana-notion-backup-alerts.yaml` and redeploy the
`monitor` stack. Grafana loads provisioning files on startup.

Alerts route through the existing notification policy to the Discord contact point —
no changes to routing or contact points are needed.

> **Note on Loki datasource UID (action required for log-errors rule):** The Loki datasource
> in `stacks/monitor/config/grafana-datasources.yaml` has no explicit `uid:` field, so Grafana
> assigns a random UID at startup. The `notion-backup-log-errors` rule uses `datasourceUid: loki`,
> which only matches if Loki's UID is actually `loki` — without a match the rule fails to load.
>
> **Recommended fix:** add `uid: loki` to the Loki datasource entry in
> `stacks/monitor/config/grafana-datasources.yaml` (one line). Then `datasourceUid: loki` matches
> and the rule loads correctly.
>
> **Alternative:** find the auto-assigned UID via Grafana → Connections → Data sources → Loki
> (it appears in the page URL) and replace `loki` in the alert file with that value.
>
> The two Prometheus-backed rules are unaffected — Prometheus already has `uid: prometheus` set
> explicitly.

---

## How it works after deployment

- **Backups:** notion-backup runs daily at 03:00 (Europe/Berlin) and writes exports to the
  `notion-backup-data` Docker volume. Backrest ships all volumes under
  `/var/lib/docker/volumes` offsite — no extra Backrest config needed.
- **Logs:** Alloy auto-discovers the container and labels log lines with
  `stack_name="backup"` and `container="notion-backup"`. No Alloy config changes needed.
- **Metrics:** Prometheus scrapes `notion-backup:9101/metrics` every 60 seconds.
- **Alerts:** Three rules fire to Discord — backup stale (>36 h without success),
  backup failed (status ≥ 2), and error-level log lines in the last 15 m.

# External fixes (homelab & grafana repos)

These fixes live **outside this repository** and must be applied by hand in the
`denishartl/homelab` and `denishartl/grafana` repos (plus Portainer). They accompany
the application-code fix in this repo (boot-time metrics seeding), which makes the
dashboard and alerts survive container restarts.

Background: the notion-backup dashboard showed "No data" / gaps because the in-memory
metrics are wiped on every restart and only repopulated after the next daily (`0 1 * * *`)
run. The app-code change re-seeds metrics from the last backup manifest at startup. The
items below fix the alerting and a broken watchtower so notifications and auto-updates
work again.

---

## B1 — homelab: fix and extend the Notion backup alerts

**File:** `stacks/monitor/grafana/alerting/grafana-notion-backup-alerts.yaml`

### (a) Fix the broken log-errors selector

The `notion-backup-log-errors` rule targets a container name that does not exist, so it
matches **zero** log lines and can never fire. The real Loki label value is
`backup-notion-backup-1` (the Compose project/service name; the working dashboard log
panel already uses it). Change the label value:

```diff
- expr: sum(count_over_time({stack_name="backup", container="notion-backup"} | json | level=~"error|critical" [15m]))
+ expr: sum(count_over_time({stack_name="backup", container="backup-notion-backup-1"} | json | level=~"error|critical" [15m]))
```

The datasource UID (`P8E80F9AEF21F6940`) is already correct. After this fix the rule
remains a catch-all for genuine `error`/`critical` log lines (e.g. a top-level
"Backup … failed").

### (b) Add a warning-severity rule for "completed with warnings" runs

Today, runs that finish as `completed_with_warnings` (status=1) — e.g. the ~576
file-download failures — trigger **no** alert: the critical `notion-backup-failed` rule
only fires on status ≥ 2. Add a separate warning-severity rule keyed on
`notion_backup_last_run_status == 1`, which does not overlap the failed rule (status=2)
or fire on clean runs (status=0).

Append this rule under `rules:` in the `notion-backup` group:

```yaml
      - uid: notion-backup-warnings
        title: Notion backup completed with warnings
        condition: B
        data:
          - refId: A
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: prometheus
            model:
              datasource:
                type: prometheus
                uid: prometheus
              editorMode: code
              expr: notion_backup_last_run_status
              instant: true
              intervalMs: 1000
              maxDataPoints: 43200
              refId: A
          - refId: B
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: __expr__
            model:
              conditions:
                - evaluator:
                    params: [0.5, 1.5]   # within_range → fires only on status == 1 (warnings)
                    type: within_range
                  operator:
                    type: and
                  query:
                    params: [A]
                  reducer:
                    params: []
                    type: last
                  type: query
              datasource:
                type: __expr__
                uid: __expr__
              expression: A
              refId: B
              type: threshold
        noDataState: OK
        execErrState: Alerting
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Notion backup for workspace '{{ $labels.workspace }}' completed with warnings (check error logs / dashboard)."
        isPaused: false
```

> **Alternative** — alert on the raw error count instead of status. Note this *also*
> fires on hard failures, so you'd be paged at both warning and critical for a failure:
>
> ```yaml
>     expr: notion_backup_last_run_errors      # evaluator: type: gt, params: [0]
> ```

This rule depends on `notion_backup_last_run_status` being reliably present, which the
app-code seeding change guarantees across restarts.

### Sync note

The canonical copy of this file is mirrored in **this** repo at
`deploy/homelab/grafana-notion-backup-alerts.yaml` and has already been updated with the
same two changes — copy from there if convenient.

---

## B2 — homelab: fix the watchtower crash loop

**Symptom:** the `watchtower` container has been crash-looping every ~60s since
2026-06-13 02:00 with:

```
level=fatal msg="Only schedule or interval can be defined, not both."
```

While crash-looping it updates nothing, so **image auto-updates are currently disabled**
for the whole homelab.

**Root cause:** the committed `stacks/watchtower/docker-compose.yaml` is correct — it
sets only `WATCHTOWER_SCHEDULE=0 0 2 * * *` and no interval. The **running** container
has *both* a schedule and an interval. The extra interval comes from one of:

- a `WATCHTOWER_POLL_INTERVAL` environment variable set in the Portainer stack, or
- a stale `command:` / entrypoint argument like `--interval 86400` on the deployed
  container (left over from an earlier interval-based config).

**Fix:**

1. In Portainer → `watchtower` stack → Environment variables: delete any
   `WATCHTOWER_POLL_INTERVAL`.
2. Confirm no `--interval` is passed as a command/arg (the committed compose has none).
3. Redeploy the stack from the committed `docker-compose.yaml`.
4. **Verify:** the logs show `Scheduling first run: …` with no `fatal`, and the
   container stops restarting.

> After this is fixed, watchtower will resume auto-updating `notion-backup` on each new
> release — i.e. more restarts. That is expected and harmless once the app-code seeding
> change is deployed.

---

## B3 — grafana: optional dashboard polish

**File:** `notion-backup.json`, panel **"Error totals by type"**.

This panel uses an **instant** query on the raw counter `notion_backup_errors_total`, so
it reads "No data" right after a restart (counters reset to absent until the next run).
Switch it to a range-based query that tolerates counter resets:

```promql
increase(notion_backup_errors_total{workspace=~"$workspace"}[$__range])
```

All the other "No data" panels are gauges and are fixed by the app-code seeding change —
no dashboard edits are needed for them.

---

## Verification after applying B1–B3

- Loki returns data for the corrected selector:
  `count_over_time({stack_name="backup", container="backup-notion-backup-1"} | json | level=~"error|critical" [15m])`
- The `notion-backup-warnings` rule appears under Alerting → Alert rules and evaluates
  (force it by temporarily having `notion_backup_last_run_status == 1`, or wait for a
  warning run), routing to the Discord contact point.
- `watchtower` container is `running` (not restarting) and logs `Scheduling first run`.
- Dashboard "Error totals by type" panel shows values after a restart.

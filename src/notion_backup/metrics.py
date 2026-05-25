# ABOUTME: Prometheus metrics recorder for notion-backup workspace runs.
# ABOUTME: Tracks backup health, durations, counts, and errors per workspace.

import time

import prometheus_client


class BackupMetrics:
    """Records per-workspace backup run metrics into a Prometheus registry."""

    def __init__(self, registry=None):
        self.registry = registry or prometheus_client.REGISTRY

        self._last_success_timestamp = prometheus_client.Gauge(
            "notion_backup_last_success_timestamp_seconds",
            "Unix timestamp of last non-failed backup run",
            ["workspace"],
            registry=self.registry,
        )
        self._last_run_timestamp = prometheus_client.Gauge(
            "notion_backup_last_run_timestamp_seconds",
            "Unix timestamp of last backup run (any status)",
            ["workspace"],
            registry=self.registry,
        )
        self._last_run_status = prometheus_client.Gauge(
            "notion_backup_last_run_status",
            "Status of last backup run: 0=completed, 1=completed_with_warnings, 2=failed",
            ["workspace"],
            registry=self.registry,
        )
        self._runs = prometheus_client.Counter(
            "notion_backup_runs",
            "Total backup runs by workspace and status",
            ["workspace", "status"],
            registry=self.registry,
        )
        self._last_run_duration = prometheus_client.Gauge(
            "notion_backup_last_run_duration_seconds",
            "Total duration of last backup run in seconds",
            ["workspace"],
            registry=self.registry,
        )
        self._phase_duration = prometheus_client.Gauge(
            "notion_backup_last_run_phase_duration_seconds",
            "Duration of each phase in the last backup run",
            ["workspace", "phase"],
            registry=self.registry,
        )
        self._last_run_pages = prometheus_client.Gauge(
            "notion_backup_last_run_pages",
            "Pages backed up in the last run",
            ["workspace"],
            registry=self.registry,
        )
        self._last_run_databases = prometheus_client.Gauge(
            "notion_backup_last_run_databases",
            "Databases backed up in the last run",
            ["workspace"],
            registry=self.registry,
        )
        self._last_run_files = prometheus_client.Gauge(
            "notion_backup_last_run_files",
            "Files downloaded in the last run",
            ["workspace"],
            registry=self.registry,
        )
        self._last_run_file_bytes = prometheus_client.Gauge(
            "notion_backup_last_run_file_bytes",
            "Bytes downloaded in the last run",
            ["workspace"],
            registry=self.registry,
        )
        self._last_run_errors = prometheus_client.Gauge(
            "notion_backup_last_run_errors",
            "Error count in the last run",
            ["workspace"],
            registry=self.registry,
        )
        self._errors = prometheus_client.Counter(
            "notion_backup_errors",
            "Total errors by workspace and error type",
            ["workspace", "type"],
            registry=self.registry,
        )

    _STATUS_MAP = {
        "completed": 0,
        "completed_with_warnings": 1,
        "failed": 2,
    }

    def record(self, workspace: str, stats: dict) -> None:
        """Record metrics for a completed workspace backup run.

        Args:
            workspace: Workspace name used as the label value.
            stats: Dict of backup statistics as returned by backup_workspace.
        """
        now = time.time()
        status = stats["status"]

        self._last_run_timestamp.labels(workspace).set(now)
        self._last_run_status.labels(workspace).set(self._STATUS_MAP.get(status, 2))

        if status != "failed":
            self._last_success_timestamp.labels(workspace).set(now)

        self._runs.labels(workspace, status).inc()

        self._last_run_duration.labels(workspace).set(stats.get("duration_seconds", 0))
        self._last_run_pages.labels(workspace).set(stats.get("pages", 0))
        self._last_run_databases.labels(workspace).set(stats.get("databases", 0))
        self._last_run_files.labels(workspace).set(stats.get("files", 0))
        self._last_run_file_bytes.labels(workspace).set(stats.get("file_bytes", 0))
        self._last_run_errors.labels(workspace).set(stats.get("errors", 0))

        for phase, dur in stats.get("phases", {}).items():
            self._phase_duration.labels(workspace, phase).set(dur)

        for err in stats.get("error_list", []):
            self._errors.labels(workspace, err.get("type", "unknown")).inc()

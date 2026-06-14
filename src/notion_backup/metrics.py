# ABOUTME: Prometheus metrics recorder for notion-backup workspace runs.
# ABOUTME: Tracks backup health, durations, counts, and errors per workspace.

import time
from datetime import datetime

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

        self._set_run_gauges(
            workspace,
            status=status,
            run_timestamp=now,
            success_timestamp=None if status == "failed" else now,
            duration=stats.get("duration_seconds", 0),
            pages=stats.get("pages", 0),
            databases=stats.get("databases", 0),
            files=stats.get("files", 0),
            file_bytes=stats.get("file_bytes", 0),
            errors_count=stats.get("errors", 0),
            phases=stats.get("phases", {}),
        )

        self._runs.labels(workspace, status).inc()
        for err in stats.get("error_list", []):
            self._errors.labels(workspace, err.get("type", "unknown")).inc()

    def seed(self, workspace: str, manifest: dict) -> None:
        """Populate gauges from a persisted backup manifest.

        Called at startup so the metrics endpoint reflects the last run immediately,
        instead of staying empty until the next scheduled backup. Counters are left
        untouched — they legitimately reset when the process restarts.

        Args:
            workspace: Workspace name used as the label value.
            manifest: Manifest dict as written by BackupManifest.to_dict().
        """
        run_timestamp = self._parse_iso_to_epoch(manifest.get("timestamp"))
        if run_timestamp is None:
            return

        status = manifest.get("status", "completed")
        self._set_run_gauges(
            workspace,
            status=status,
            run_timestamp=run_timestamp,
            success_timestamp=None if status == "failed" else run_timestamp,
            duration=manifest.get("duration_seconds", 0),
            pages=manifest.get("pages_backed_up", 0),
            databases=manifest.get("databases_backed_up", 0),
            files=manifest.get("files_downloaded", 0),
            file_bytes=manifest.get("file_bytes", 0),
            errors_count=len(manifest.get("errors", [])),
            phases=manifest.get("phase_durations", {}),
        )

    def _set_run_gauges(
        self,
        workspace: str,
        *,
        status: str,
        run_timestamp: float,
        success_timestamp: float | None,
        duration: float,
        pages: int,
        databases: int,
        files: int,
        file_bytes: int,
        errors_count: int,
        phases: dict,
    ) -> None:
        """Set every per-run gauge for a workspace. Shared by record() and seed()."""
        self._last_run_timestamp.labels(workspace).set(run_timestamp)
        self._last_run_status.labels(workspace).set(self._STATUS_MAP.get(status, 2))

        if success_timestamp is not None:
            self._last_success_timestamp.labels(workspace).set(success_timestamp)

        self._last_run_duration.labels(workspace).set(duration)
        self._last_run_pages.labels(workspace).set(pages)
        self._last_run_databases.labels(workspace).set(databases)
        self._last_run_files.labels(workspace).set(files)
        self._last_run_file_bytes.labels(workspace).set(file_bytes)
        self._last_run_errors.labels(workspace).set(errors_count)

        for phase, dur in phases.items():
            self._phase_duration.labels(workspace, phase).set(dur)

    @staticmethod
    def _parse_iso_to_epoch(timestamp: str | None) -> float | None:
        """Parse an ISO-8601 timestamp (with trailing 'Z') to a Unix epoch, or None."""
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
        except (ValueError, AttributeError):
            return None

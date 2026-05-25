# ABOUTME: Tests for the BackupMetrics Prometheus metrics recorder.
# ABOUTME: Uses isolated CollectorRegistry instances to avoid cross-test pollution.

import prometheus_client

from notion_backup.metrics import BackupMetrics


def make_registry():
    """Return a fresh CollectorRegistry for test isolation."""
    return prometheus_client.CollectorRegistry()


def val(registry, name, labels):
    """Read a single sample value from the registry."""
    return registry.get_sample_value(name, labels)


class TestCompletedRun:
    def setup_method(self):
        self.registry = make_registry()
        self.m = BackupMetrics(registry=self.registry)
        self.stats = {
            "status": "completed",
            "pages": 42,
            "databases": 3,
            "files": 10,
            "file_bytes": 1048576,
            "errors": 0,
            "duration_seconds": 95.5,
            "error_list": [],
            "phases": {},
        }
        self.m.record("personal", self.stats)

    def test_last_run_pages(self):
        assert val(self.registry, "notion_backup_last_run_pages", {"workspace": "personal"}) == 42

    def test_last_run_databases(self):
        assert val(self.registry, "notion_backup_last_run_databases", {"workspace": "personal"}) == 3

    def test_last_run_files(self):
        assert val(self.registry, "notion_backup_last_run_files", {"workspace": "personal"}) == 10

    def test_last_run_file_bytes(self):
        assert val(self.registry, "notion_backup_last_run_file_bytes", {"workspace": "personal"}) == 1048576

    def test_last_run_errors(self):
        assert val(self.registry, "notion_backup_last_run_errors", {"workspace": "personal"}) == 0

    def test_last_run_duration_seconds(self):
        assert val(self.registry, "notion_backup_last_run_duration_seconds", {"workspace": "personal"}) == 95.5

    def test_last_run_status_is_zero(self):
        assert val(self.registry, "notion_backup_last_run_status", {"workspace": "personal"}) == 0

    def test_last_success_timestamp_is_set(self):
        assert val(self.registry, "notion_backup_last_success_timestamp_seconds", {"workspace": "personal"}) > 0

    def test_last_run_timestamp_is_set(self):
        assert val(self.registry, "notion_backup_last_run_timestamp_seconds", {"workspace": "personal"}) > 0

    def test_runs_total_completed_is_one(self):
        assert val(self.registry, "notion_backup_runs_total", {"workspace": "personal", "status": "completed"}) == 1


class TestFailedRun:
    def setup_method(self):
        self.registry = make_registry()
        self.m = BackupMetrics(registry=self.registry)
        self.stats = {
            "status": "failed",
            "pages": 0,
            "databases": 0,
            "files": 0,
            "errors": 1,
            "error_list": [{"type": "backup", "error": "connection refused"}],
        }
        self.m.record("personal", self.stats)

    def test_last_run_status_is_two(self):
        assert val(self.registry, "notion_backup_last_run_status", {"workspace": "personal"}) == 2

    def test_last_success_timestamp_not_set(self):
        # Must be None — never-succeeded workspace should not produce a stale-alert false positive
        assert val(self.registry, "notion_backup_last_success_timestamp_seconds", {"workspace": "personal"}) is None

    def test_runs_total_failed_is_one(self):
        assert val(self.registry, "notion_backup_runs_total", {"workspace": "personal", "status": "failed"}) == 1

    def test_errors_total_backup_type(self):
        assert val(self.registry, "notion_backup_errors_total", {"workspace": "personal", "type": "backup"}) == 1


class TestCompletedWithWarnings:
    def setup_method(self):
        self.registry = make_registry()
        self.m = BackupMetrics(registry=self.registry)
        self.stats = {
            "status": "completed_with_warnings",
            "pages": 5,
            "databases": 0,
            "files": 0,
            "errors": 2,
            "error_list": [],
        }
        self.m.record("personal", self.stats)

    def test_last_run_status_is_one(self):
        assert val(self.registry, "notion_backup_last_run_status", {"workspace": "personal"}) == 1

    def test_last_success_timestamp_is_set(self):
        assert val(self.registry, "notion_backup_last_success_timestamp_seconds", {"workspace": "personal"}) > 0


class TestPhaseDurations:
    def setup_method(self):
        self.registry = make_registry()
        self.m = BackupMetrics(registry=self.registry)
        self.stats = {
            "status": "completed",
            "pages": 1,
            "databases": 0,
            "files": 0,
            "errors": 0,
            "error_list": [],
            "phases": {"pages": 12.5, "files": 3.0},
        }
        self.m.record("personal", self.stats)

    def test_phase_pages_duration(self):
        assert val(
            self.registry,
            "notion_backup_last_run_phase_duration_seconds",
            {"workspace": "personal", "phase": "pages"},
        ) == 12.5

    def test_phase_files_duration(self):
        assert val(
            self.registry,
            "notion_backup_last_run_phase_duration_seconds",
            {"workspace": "personal", "phase": "files"},
        ) == 3.0


class TestErrorListCounting:
    def setup_method(self):
        self.registry = make_registry()
        self.m = BackupMetrics(registry=self.registry)
        self.stats = {
            "status": "completed_with_warnings",
            "pages": 10,
            "databases": 0,
            "files": 0,
            "errors": 3,
            "error_list": [
                {"type": "page", "error": "not found"},
                {"type": "page", "error": "timeout"},
                {"type": "file", "error": "download failed"},
            ],
        }
        self.m.record("personal", self.stats)

    def test_errors_total_page_type_is_two(self):
        assert val(self.registry, "notion_backup_errors_total", {"workspace": "personal", "type": "page"}) == 2

    def test_errors_total_file_type_is_one(self):
        assert val(self.registry, "notion_backup_errors_total", {"workspace": "personal", "type": "file"}) == 1


class TestCounterAccumulation:
    def setup_method(self):
        self.registry = make_registry()
        self.m = BackupMetrics(registry=self.registry)
        # First run: completed, one page error
        self.m.record("personal", {
            "status": "completed",
            "pages": 10,
            "databases": 0,
            "files": 0,
            "file_bytes": 0,
            "errors": 1,
            "duration_seconds": 30.0,
            "error_list": [{"type": "page", "error": "timeout"}],
            "phases": {},
        })
        # Second run: completed_with_warnings, one more page error
        self.m.record("personal", {
            "status": "completed_with_warnings",
            "pages": 5,
            "databases": 0,
            "files": 0,
            "file_bytes": 0,
            "errors": 1,
            "duration_seconds": 15.0,
            "error_list": [{"type": "page", "error": "not found"}],
            "phases": {},
        })

    def test_runs_total_completed_is_one(self):
        assert val(self.registry, "notion_backup_runs_total", {"workspace": "personal", "status": "completed"}) == 1

    def test_runs_total_completed_with_warnings_is_one(self):
        assert val(self.registry, "notion_backup_runs_total", {"workspace": "personal", "status": "completed_with_warnings"}) == 1

    def test_errors_total_accumulates_across_runs(self):
        # Both runs contributed a page error — counter must reflect both
        assert val(self.registry, "notion_backup_errors_total", {"workspace": "personal", "type": "page"}) == 2

    def test_last_run_pages_reflects_second_run(self):
        # Gauge is overwritten on each call — only the latest value should remain
        assert val(self.registry, "notion_backup_last_run_pages", {"workspace": "personal"}) == 5

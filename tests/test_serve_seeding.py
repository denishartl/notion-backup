# ABOUTME: Tests for seed_metrics_from_disk, the startup metric seeding loader.
# ABOUTME: Verifies it reads the latest manifest per workspace and tolerates bad input.

import json
from datetime import datetime

import prometheus_client

from notion_backup.__main__ import seed_metrics_from_disk
from notion_backup.config import Config, WorkspaceConfig
from notion_backup.metrics import BackupMetrics


def make_config(*names):
    return Config(
        schedule="0 1 * * *",
        retention_count=7,
        workspaces=[WorkspaceConfig(name=n, token_env=f"TOK_{n}") for n in names],
    )


def write_backup(backup_path, workspace, dir_name, manifest):
    d = backup_path / workspace / dir_name
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def val(registry, name, labels):
    return registry.get_sample_value(name, labels)


def test_seeds_from_latest_manifest(tmp_path):
    backup_path = tmp_path / "backups"
    # Older run: completed; newer run: warnings — the newer one must win.
    write_backup(backup_path, "personal", "2026-06-13_010000", {
        "timestamp": "2026-06-13T01:00:00Z", "status": "completed",
        "pages_backed_up": 1, "errors": [], "phase_durations": {},
    })
    write_backup(backup_path, "personal", "2026-06-14_010000", {
        "timestamp": "2026-06-14T01:00:00Z", "status": "completed_with_warnings",
        "pages_backed_up": 42, "errors": [{"type": "file"}], "phase_durations": {},
    })

    registry = prometheus_client.CollectorRegistry()
    metrics = BackupMetrics(registry=registry)
    seed_metrics_from_disk(metrics, make_config("personal"), backup_path)

    assert val(registry, "notion_backup_last_run_pages", {"workspace": "personal"}) == 42
    assert val(registry, "notion_backup_last_run_status", {"workspace": "personal"}) == 1
    expected = datetime.fromisoformat("2026-06-14T01:00:00+00:00").timestamp()
    assert val(registry, "notion_backup_last_run_timestamp_seconds", {"workspace": "personal"}) == expected


def test_skips_workspace_without_backups(tmp_path):
    registry = prometheus_client.CollectorRegistry()
    metrics = BackupMetrics(registry=registry)
    # No backup dirs created at all — must not raise, must not seed.
    seed_metrics_from_disk(metrics, make_config("personal"), tmp_path / "backups")
    assert val(registry, "notion_backup_last_run_status", {"workspace": "personal"}) is None


def test_tolerates_corrupt_manifest(tmp_path):
    backup_path = tmp_path / "backups"
    d = backup_path / "personal" / "2026-06-14_010000"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text("{not valid json", encoding="utf-8")

    registry = prometheus_client.CollectorRegistry()
    metrics = BackupMetrics(registry=registry)
    seed_metrics_from_disk(metrics, make_config("personal"), backup_path)  # must not raise
    assert val(registry, "notion_backup_last_run_status", {"workspace": "personal"}) is None

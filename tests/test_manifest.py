# ABOUTME: Tests for backup manifest creation and serialization.
# ABOUTME: Covers the persisted fields used to seed metrics on startup.

from datetime import datetime, timezone

from notion_backup.backup.manifest import BackupManifest, create_manifest


def test_create_manifest_persists_file_bytes_and_phase_durations():
    start = datetime(2026, 6, 14, 1, 0, 0, tzinfo=timezone.utc)
    manifest = create_manifest(
        start_time=start,
        pages_count=10,
        databases_count=2,
        files_count=4,
        errors=[],
        file_bytes=2048,
        phase_durations={"pages": 5.0, "files": 1.5},
    )

    assert manifest.file_bytes == 2048
    assert manifest.phase_durations == {"pages": 5.0, "files": 1.5}


def test_manifest_to_dict_round_trips_new_fields():
    manifest = BackupManifest(
        timestamp="2026-06-14T01:00:00Z",
        file_bytes=4096,
        phase_durations={"discover": 0.5},
    )
    d = manifest.to_dict()

    assert d["file_bytes"] == 4096
    assert d["phase_durations"] == {"discover": 0.5}


def test_create_manifest_defaults_for_new_fields():
    start = datetime(2026, 6, 14, 1, 0, 0, tzinfo=timezone.utc)
    manifest = create_manifest(
        start_time=start,
        pages_count=1,
        databases_count=0,
        files_count=0,
        errors=[],
    )

    assert manifest.file_bytes == 0
    assert manifest.phase_durations == {}

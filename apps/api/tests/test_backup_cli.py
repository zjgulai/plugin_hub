from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from plugin_hub_api.backup_cli import create_verified_backup, verify_sqlite_backup


def test_create_verified_backup_is_consistent_and_prunes_only_after_success(
    tmp_path: Path,
) -> None:
    source = tmp_path / "plugin_hub.db"
    destination = tmp_path / "backups"
    with sqlite3.connect(source) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE collection_runs (id TEXT PRIMARY KEY)")
        connection.executemany(
            "INSERT INTO collection_runs (id) VALUES (?)",
            [("run-1",), ("run-2",)],
        )

    started_at = datetime(2026, 7, 10, 3, 15, tzinfo=UTC)
    results = [
        create_verified_backup(
            source=source,
            destination_dir=destination,
            retention_count=2,
            now=started_at + timedelta(days=offset),
        )
        for offset in range(3)
    ]

    backups = sorted(destination.glob("plugin_hub_*.db"))
    assert backups == [results[1].backup_path, results[2].backup_path]
    verification = verify_sqlite_backup(results[2].backup_path)
    assert verification.quick_check_ok is True
    assert verification.table_counts == {"collection_runs": 2}
    manifest = json.loads(results[2].manifest_path.read_text())
    assert manifest["quick_check_ok"] is True
    assert manifest["table_counts"] == {"collection_runs": 2}
    assert len(manifest["sha256"]) == 64
    assert results[0].backup_path.exists() is False
    assert results[0].manifest_path.exists() is False
    assert destination.stat().st_mode & 0o777 == 0o700
    assert (destination / ".plugin_hub_backup.lock").stat().st_mode & 0o777 == 0o600
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in destination.iterdir())
    assert not any(
        path.name.endswith(("-wal", "-shm")) or ".tmp" in path.name
        for path in destination.iterdir()
    )


def test_retention_does_not_count_tampered_backup_as_verified(tmp_path: Path) -> None:
    source = tmp_path / "plugin_hub.db"
    destination = tmp_path / "backups"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE raw_source_items (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO raw_source_items DEFAULT VALUES")

    started_at = datetime(2026, 7, 10, 3, 15, tzinfo=UTC)
    oldest = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at,
    )
    tampered = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at + timedelta(days=1),
    )
    with tampered.backup_path.open("ab") as file_handle:
        file_handle.write(b"tampered")

    newest = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at + timedelta(days=2),
    )

    assert oldest.backup_path.exists() is True
    assert tampered.backup_path.exists() is True
    assert newest.backup_path.exists() is True

    next_backup = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at + timedelta(days=3),
    )

    assert oldest.backup_path.exists() is False
    assert tampered.backup_path.exists() is True
    assert newest.backup_path.exists() is True
    assert next_backup.backup_path.exists() is True

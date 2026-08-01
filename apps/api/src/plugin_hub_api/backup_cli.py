from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class BackupVerification:
    quick_check_ok: bool
    foreign_key_issues: int
    table_counts: dict[str, int]


@dataclass(frozen=True)
class BackupResult:
    backup_path: Path
    manifest_path: Path
    sha256: str
    bytes_written: int


def create_verified_backup(
    *,
    source: Path,
    destination_dir: Path,
    retention_count: int,
    now: datetime | None = None,
) -> BackupResult:
    if retention_count < 2:
        raise ValueError("backup_retention_count_must_be_at_least_two")
    resolved_source = source.resolve(strict=True)
    destination_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(destination_dir, 0o700)
    timestamp = (now or datetime.now(tz=UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = destination_dir / f"plugin_hub_{timestamp}.db"
    manifest_path = destination_dir / f"plugin_hub_{timestamp}.manifest.json"
    temporary_path = destination_dir / f".plugin_hub_{timestamp}.db.tmp"
    lock_path = destination_dir / ".plugin_hub_backup.lock"

    with lock_path.open("a+", encoding="utf-8") as lock_file:
        os.fchmod(lock_file.fileno(), 0o600)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        if backup_path.exists() or manifest_path.exists():
            raise FileExistsError("backup_timestamp_already_exists")
        _unlink_sqlite_files(temporary_path)
        try:
            _sqlite_backup(resolved_source, temporary_path)
            verification = verify_sqlite_backup(temporary_path)
            if not verification.quick_check_ok:
                raise RuntimeError("backup_quick_check_failed")
            if verification.foreign_key_issues:
                raise RuntimeError("backup_foreign_key_check_failed")
            os.chmod(temporary_path, 0o600)
            digest = _sha256(temporary_path)
            bytes_written = temporary_path.stat().st_size
            os.replace(temporary_path, backup_path)
            _write_manifest(
                manifest_path=manifest_path,
                backup_path=backup_path,
                created_at=(now or datetime.now(tz=UTC)).astimezone(UTC),
                sha256=digest,
                bytes_written=bytes_written,
                verification=verification,
            )
            _prune_verified_backups(destination_dir, retention_count=retention_count)
        finally:
            _unlink_sqlite_files(temporary_path)

    return BackupResult(
        backup_path=backup_path,
        manifest_path=manifest_path,
        sha256=digest,
        bytes_written=bytes_written,
    )


def verify_sqlite_backup(path: Path) -> BackupVerification:
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro&immutable=1",
        uri=True,
        timeout=10,
    )
    try:
        connection.execute("PRAGMA query_only=ON")
        quick_check = connection.execute("PRAGMA quick_check").fetchall()
        foreign_key_issues = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        tables = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        table_counts = {
            table: int(
                connection.execute(f"SELECT COUNT(*) FROM {_quote_identifier(table)}").fetchone()[0]
            )
            for table in tables
        }
        return BackupVerification(
            quick_check_ok=quick_check == [("ok",)],
            foreign_key_issues=foreign_key_issues,
            table_counts=table_counts,
        )
    finally:
        connection.close()


def _sqlite_backup(source: Path, destination: Path) -> None:
    # The source file already exists (resolved with strict=True by the caller).
    # Open it read-write so SQLite can recover a hot journal or WAL index before
    # the online backup starts, then block application-issued mutation SQL.
    source_connection = sqlite3.connect(
        f"{source.as_uri()}?mode=rw",
        uri=True,
        timeout=30,
    )
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.execute("PRAGMA query_only=ON")
        source_connection.backup(destination_connection)
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()


def _write_manifest(
    *,
    manifest_path: Path,
    backup_path: Path,
    created_at: datetime,
    sha256: str,
    bytes_written: int,
    verification: BackupVerification,
) -> None:
    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    payload = {
        "backup_file": backup_path.name,
        "created_at": created_at.isoformat(),
        "sha256": sha256,
        "bytes": bytes_written,
        "quick_check_ok": verification.quick_check_ok,
        "foreign_key_issues": verification.foreign_key_issues,
        "table_counts": verification.table_counts,
    }
    temporary_manifest.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary_manifest, 0o600)
    os.replace(temporary_manifest, manifest_path)


def _prune_verified_backups(destination_dir: Path, *, retention_count: int) -> None:
    backup_paths = sorted(destination_dir.glob("plugin_hub_*.db"), reverse=True)
    verified_backup_paths = [
        backup_path
        for backup_path in backup_paths
        if _manifest_matches_backup(
            backup_path,
            backup_path.with_suffix(".manifest.json"),
        )
    ]
    for backup_path in verified_backup_paths[retention_count:]:
        manifest_path = backup_path.with_suffix(".manifest.json")
        _unlink_sqlite_files(backup_path)
        manifest_path.unlink()


def _manifest_matches_backup(backup_path: Path, manifest_path: Path) -> bool:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return False
        if manifest.get("backup_file") != backup_path.name:
            return False
        if manifest.get("bytes") != backup_path.stat().st_size:
            return False
        if manifest.get("sha256") != _sha256(backup_path):
            return False
        verification = verify_sqlite_backup(backup_path)
        return (
            manifest.get("quick_check_ok") is True
            and verification.quick_check_ok
            and manifest.get("foreign_key_issues") == 0
            and verification.foreign_key_issues == 0
            and manifest.get("table_counts") == verification.table_counts
        )
    except (OSError, ValueError, sqlite3.Error):
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unlink_sqlite_files(path: Path) -> None:
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        candidate.unlink(missing_ok=True)


def _quote_identifier(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a verified Plugin Hub SQLite backup.")
    parser.add_argument("--source", type=Path, default=Path("/data/plugin_hub.db"))
    parser.add_argument("--destination-dir", type=Path, default=Path("/backups"))
    parser.add_argument("--retention-count", type=int, default=14)
    args = parser.parse_args()
    result = create_verified_backup(
        source=args.source,
        destination_dir=args.destination_dir,
        retention_count=args.retention_count,
    )
    print(
        json.dumps(
            {
                "status": "verified",
                "backup_file": result.backup_path.name,
                "manifest_file": result.manifest_path.name,
                "bytes": result.bytes_written,
                "sha256": result.sha256,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote

from sqlalchemy.engine import make_url

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine
from plugin_hub_api.migrations import (
    applied_migration_versions,
    apply_pending_migrations,
    migration_versions_from_applied_checksums,
    rollback_latest_migration,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage explicit Plugin Hub schema migrations.")
    parser.add_argument("action", choices=("status", "up", "down"))
    parser.add_argument("--database-url")
    args = parser.parse_args()

    settings = Settings()
    database_url = args.database_url or settings.database_url
    if args.action == "status":
        try:
            applied_versions = _read_migration_status(
                database_url,
                sqlite_busy_timeout_ms=settings.sqlite_busy_timeout_ms,
            )
        except FileNotFoundError as error:
            parser.error(str(error))
        _print_status(action=args.action, applied_versions=applied_versions, changed=[])
        return

    engine = build_engine(
        database_url,
        sqlite_busy_timeout_ms=settings.sqlite_busy_timeout_ms,
        sqlite_wal_enabled=settings.sqlite_wal_enabled,
    )
    try:
        if args.action == "up":
            changed = apply_pending_migrations(engine)
        else:
            rolled_back = rollback_latest_migration(engine)
            changed = [rolled_back] if rolled_back is not None else []
        _print_status(
            action=args.action,
            applied_versions=applied_migration_versions(engine),
            changed=changed,
        )
    finally:
        engine.dispose()


def _read_migration_status(database_url: str, *, sqlite_busy_timeout_ms: int) -> list[str]:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        engine = build_engine(database_url)
        try:
            return applied_migration_versions(engine)
        finally:
            engine.dispose()

    database = url.database
    if database is None or database == ":memory:":
        return []
    database_path = Path(database).expanduser().resolve()
    if not database_path.is_file():
        raise FileNotFoundError(f"sqlite_database_not_found:{database_path}")

    uri_path = quote(str(database_path), safe="/")
    with sqlite3.connect(
        f"file:{uri_path}?mode=ro",
        uri=True,
        timeout=sqlite_busy_timeout_ms / 1_000,
    ) as connection:
        connection.execute("PRAGMA query_only=ON")
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchone()
        if table_exists is None:
            return []
        rows = connection.execute(
            "SELECT version, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
    applied = {str(version): str(checksum) for version, checksum in rows}
    return migration_versions_from_applied_checksums(applied)


def _print_status(*, action: str, applied_versions: list[str], changed: list[str]) -> None:
    print(
        json.dumps(
            {
                "action": action,
                "applied_versions": applied_versions,
                "changed_versions": changed,
                "status": "ok",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

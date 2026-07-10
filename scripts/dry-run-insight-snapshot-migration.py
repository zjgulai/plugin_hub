#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from plugin_hub_api.config import Settings
from plugin_hub_api.main import create_app
from plugin_hub_api.migrations import (
    MigrationRollbackBlocked,
    applied_migration_versions,
    apply_pending_migrations,
    rollback_latest_migration,
)

CORE_TABLES = ("collection_runs", "raw_source_items", "canonical_voc_units")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply and verify the insight snapshot migration on a copied SQLite DB."
    )
    parser.add_argument("--database-path", type=Path, required=True)
    parser.add_argument("--copied-database", action="store_true")
    args = parser.parse_args()

    database_path = args.database_path.resolve(strict=True)
    if not args.copied_database:
        raise SystemExit("copied_database_confirmation_required")
    if str(database_path).startswith("/opt/plugin-hub/data/"):
        raise SystemExit("live_production_database_refused")

    database_url = f"sqlite+pysqlite:///{database_path}"
    before_counts = _table_counts(database_path)
    settings = Settings(
        database_url=database_url,
        sqlite_busy_timeout_ms=15_000,
        sqlite_wal_enabled=True,
        api_auth_mode="disabled",
    )
    app = create_app(database_url=database_url, settings=settings)
    applied_now = apply_pending_migrations(app.state.engine)

    snapshot_results: dict[str, dict[str, object]] = {}
    with TestClient(app) as client:
        for platform in ("amazon", "reddit"):
            first = client.post(
                "/api/insights/snapshots",
                json={"platform": platform, "language": "zh-CN"},
            )
            first.raise_for_status()
            second = client.post(
                "/api/insights/snapshots",
                json={"platform": platform, "language": "zh-CN"},
            )
            second.raise_for_status()
            first_payload = first.json()
            second_payload = second.json()
            assert first_payload["replayed"] is False
            assert second_payload["replayed"] is True
            assert first_payload["run"] == second_payload["run"]
            snapshot_results[platform] = {
                "analysis_run_id": first_payload["run"]["analysis_run_id"],
                "analysis_unit_count": first_payload["run"]["analysis_unit_count"],
                "artifact_count": first_payload["run"]["artifact_count"],
                "source_unit_count": first_payload["run"]["source_unit_count"],
            }

    with app.state.engine.connect() as connection:
        artifact_counts = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                text(
                    """
                    SELECT artifact_type, COUNT(*)
                    FROM analysis_artifact_snapshots
                    GROUP BY artifact_type
                    ORDER BY artifact_type
                    """
                )
            ).all()
        }
        snapshot_run_count = int(
            connection.execute(text("SELECT COUNT(*) FROM analysis_runs")).scalar_one()
        )

    trigger_enforced = False
    try:
        with app.state.engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE analysis_runs SET language = 'en-US' WHERE platform = 'amazon'"
            )
    except DatabaseError as error:
        trigger_enforced = "analysis_runs_append_only" in str(error)
    assert trigger_enforced

    rollback_blocked = False
    try:
        rollback_latest_migration(app.state.engine)
    except MigrationRollbackBlocked as error:
        rollback_blocked = str(error) == "analysis_snapshot_rows_exist"
    assert rollback_blocked

    after_counts = _table_counts(database_path)
    assert after_counts == before_counts
    quick_check, foreign_key_issues = _integrity(database_path)
    assert quick_check == "ok"
    assert foreign_key_issues == 0
    assert snapshot_run_count == 2

    print(
        json.dumps(
            {
                "applied_now": applied_now,
                "applied_versions": applied_migration_versions(app.state.engine),
                "artifact_counts": artifact_counts,
                "core_counts_after": after_counts,
                "core_counts_before": before_counts,
                "core_counts_unchanged": True,
                "foreign_key_issues": foreign_key_issues,
                "quick_check": quick_check,
                "rollback_blocked_after_snapshot": rollback_blocked,
                "snapshot_run_count": snapshot_run_count,
                "snapshot_runs": snapshot_results,
                "status": "pass",
                "trigger_enforced": trigger_enforced,
            },
            sort_keys=True,
        )
    )
    app.state.engine.dispose()


def _table_counts(database_path: Path) -> dict[str, int]:
    connection = sqlite3.connect(
        f"{database_path.as_uri()}?mode=ro",
        uri=True,
    )
    try:
        connection.execute("PRAGMA query_only=ON")
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in CORE_TABLES
        }
    finally:
        connection.close()


def _integrity(database_path: Path) -> tuple[str, int]:
    connection = sqlite3.connect(
        f"{database_path.as_uri()}?mode=ro",
        uri=True,
    )
    try:
        connection.execute("PRAGMA query_only=ON")
        quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        foreign_key_issues = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        return quick_check, foreign_key_issues
    finally:
        connection.close()


if __name__ == "__main__":
    main()

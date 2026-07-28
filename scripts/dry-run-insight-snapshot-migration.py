#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DatabaseError

from plugin_hub_api.config import Settings
from plugin_hub_api.main import create_app
from plugin_hub_api.migrations import (
    ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    MigrationRollbackBlocked,
    applied_migration_versions,
    apply_pending_migrations,
    rollback_latest_migration,
)

CORE_TABLES = ("collection_runs", "raw_source_items", "canonical_voc_units")
LIVE_DATABASE_ROOTS = (Path("/opt/plugin-hub/data"), Path("/data"))
INSERT_GUARD_TRIGGERS = frozenset(
    {"analysis_runs_no_replace", "analysis_artifacts_no_replace"}
)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


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
    refuse_live_database_path(database_path)

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
    applied_versions = applied_migration_versions(app.state.engine)
    migration_checksum_verified = (
        ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION in applied_versions
    )
    require(
        migration_checksum_verified,
        "analysis_snapshot_insert_guard_migration_not_applied",
    )
    insert_guard_triggers = _insert_guard_trigger_names(app.state.engine)
    require(
        insert_guard_triggers == INSERT_GUARD_TRIGGERS,
        "analysis_snapshot_insert_guard_triggers_missing",
    )
    baseline_snapshot_run_count = _snapshot_run_count(app.state.engine)

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
            require(
                second_payload["replayed"] is True,
                f"snapshot_replay_not_idempotent:{platform}",
            )
            require(
                first_payload["run"] == second_payload["run"],
                f"snapshot_replay_payload_mismatch:{platform}",
            )
            snapshot_results[platform] = {
                "analysis_run_id": first_payload["run"]["analysis_run_id"],
                "analysis_unit_count": first_payload["run"]["analysis_unit_count"],
                "artifact_count": first_payload["run"]["artifact_count"],
                "initially_replayed": first_payload["replayed"],
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
    require(trigger_enforced, "analysis_snapshot_append_only_trigger_not_enforced")

    run_replace_guard_enforced = _run_replace_guard_enforced(app.state.engine)
    require(
        run_replace_guard_enforced,
        "analysis_snapshot_run_replace_guard_not_enforced",
    )
    artifact_replace_guard_enforced = _artifact_replace_guard_enforced(
        app.state.engine
    )
    require(
        artifact_replace_guard_enforced,
        "analysis_snapshot_artifact_replace_guard_not_enforced",
    )

    rollback_blocked = False
    try:
        rollback_latest_migration(app.state.engine)
    except MigrationRollbackBlocked as error:
        rollback_blocked = str(error) == "analysis_snapshot_rows_exist"
    require(rollback_blocked, "analysis_snapshot_rollback_not_blocked")

    after_counts = _table_counts(database_path)
    require(after_counts == before_counts, "core_table_counts_changed")
    quick_check, foreign_key_issues = _integrity(database_path)
    require(quick_check == "ok", "database_quick_check_failed")
    require(foreign_key_issues == 0, "database_foreign_key_issues")
    expected_snapshot_run_count = baseline_snapshot_run_count + sum(
        not bool(result["initially_replayed"])
        for result in snapshot_results.values()
    )
    require(
        snapshot_run_count == expected_snapshot_run_count,
        "snapshot_run_count_mismatch",
    )

    print(
        json.dumps(
            {
                "applied_now": applied_now,
                "applied_versions": applied_versions,
                "artifact_counts": artifact_counts,
                "artifact_replace_guard_enforced": artifact_replace_guard_enforced,
                "baseline_snapshot_run_count": baseline_snapshot_run_count,
                "core_counts_after": after_counts,
                "core_counts_before": before_counts,
                "core_counts_unchanged": True,
                "foreign_key_issues": foreign_key_issues,
                "insert_guard_triggers": sorted(insert_guard_triggers),
                "migration_checksum_verified": migration_checksum_verified,
                "quick_check": quick_check,
                "rollback_blocked_after_snapshot": rollback_blocked,
                "run_replace_guard_enforced": run_replace_guard_enforced,
                "snapshot_run_count": snapshot_run_count,
                "snapshot_runs": snapshot_results,
                "status": "pass",
                "trigger_enforced": trigger_enforced,
            },
            sort_keys=True,
        )
    )
    app.state.engine.dispose()


def refuse_live_database_path(database_path: Path) -> None:
    if any(
        database_path == live_root or live_root in database_path.parents
        for live_root in LIVE_DATABASE_ROOTS
    ):
        raise SystemExit("live_production_database_refused")


def _snapshot_run_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text("SELECT COUNT(*) FROM analysis_runs")).scalar_one())


def _insert_guard_trigger_names(engine: Engine) -> frozenset[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'trigger' AND name IN (
                    'analysis_runs_no_replace',
                    'analysis_artifacts_no_replace'
                )
                """
            )
        ).all()
    return frozenset(str(row[0]) for row in rows)


def _run_replace_guard_enforced(engine: Engine) -> bool:
    with engine.connect() as connection:
        analysis_run_id = connection.execute(
            text("SELECT analysis_run_id FROM analysis_runs ORDER BY analysis_run_id LIMIT 1")
        ).scalar_one()
        return _statement_rejected(
            connection,
            """
            INSERT OR REPLACE INTO analysis_runs
            SELECT * FROM analysis_runs WHERE analysis_run_id = :analysis_run_id
            """,
            {"analysis_run_id": analysis_run_id},
            "analysis_runs_append_only",
        )


def _artifact_replace_guard_enforced(engine: Engine) -> bool:
    with engine.connect() as connection:
        artifact_id = connection.execute(
            text(
                """
                SELECT analysis_snapshot_id
                FROM analysis_artifact_snapshots
                ORDER BY analysis_snapshot_id
                LIMIT 1
                """
            )
        ).scalar_one_or_none()
        if artifact_id is not None:
            statement = """
                INSERT OR REPLACE INTO analysis_artifact_snapshots
                SELECT * FROM analysis_artifact_snapshots
                WHERE analysis_snapshot_id = :analysis_snapshot_id
            """
            parameters = {"analysis_snapshot_id": artifact_id}
        else:
            analysis_run_id = connection.execute(
                text(
                    "SELECT analysis_run_id FROM analysis_runs "
                    "ORDER BY analysis_run_id LIMIT 1"
                )
            ).scalar_one()
            statement = """
                INSERT OR REPLACE INTO analysis_artifact_snapshots (
                    analysis_snapshot_id, analysis_run_id, artifact_type,
                    artifact_key, schema_version, payload_json, payload_digest,
                    created_at
                ) VALUES (
                    'dry-run-insert-guard-probe', :analysis_run_id, 'strategy_note',
                    'dry-run-insert-guard-probe', 'v1', '{}', 'sha256:probe',
                    '2026-07-28T00:00:00+00:00'
                )
            """
            parameters = {"analysis_run_id": analysis_run_id}
        return _statement_rejected(
            connection,
            statement,
            parameters,
            "analysis_artifacts_append_only",
        )


def _statement_rejected(
    connection: Connection,
    statement: str,
    parameters: dict[str, object],
    expected_error: str,
) -> bool:
    # The probe selectors above use SQLAlchemy autobegin. End that read-only
    # transaction before opening a rollback-only mutation probe.
    connection.rollback()
    transaction = connection.begin()
    try:
        connection.execute(text(statement), parameters)
    except DatabaseError as error:
        return expected_error in str(error)
    finally:
        transaction.rollback()
    return False


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

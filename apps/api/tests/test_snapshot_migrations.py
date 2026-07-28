from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest
from sqlalchemy.exc import DatabaseError

import plugin_hub_api.migrations as migration_module
from plugin_hub_api.db import build_engine, init_database
from plugin_hub_api.migration_cli import main as migration_cli_main
from plugin_hub_api.migrations import (
    ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    ANALYSIS_SNAPSHOT_MIGRATION,
    ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
    MIGRATION_TABLE_SQL,
    MIGRATIONS,
    MIGRATIONS_BY_VERSION,
    Migration,
    MigrationChecksumMismatch,
    MigrationRollbackBlocked,
    applied_migration_versions,
    apply_pending_migrations,
    rollback_latest_migration,
)


def test_analysis_snapshot_migration_is_idempotent_and_reversible_when_empty(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)

    first = apply_pending_migrations(engine)
    second = apply_pending_migrations(engine)

    assert first == [
        ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
        ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    ]
    assert second == []
    assert applied_migration_versions(engine) == [
        ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
        ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    ]

    guards_rolled_back = rollback_latest_migration(engine)
    schema_rolled_back = rollback_latest_migration(engine)

    assert guards_rolled_back == ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION
    assert schema_rolled_back == ANALYSIS_SNAPSHOT_MIGRATION_VERSION
    assert applied_migration_versions(engine) == []
    engine.dispose()


def test_existing_0001_database_upgrades_without_checksum_drift(tmp_path: Path) -> None:
    assert ANALYSIS_SNAPSHOT_MIGRATION.checksum == (
        "cf0a110bb9230d49c01a9ce4f36d9f403d36ba4502a2bffd313a65773c189695"
    )
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(MIGRATION_TABLE_SQL)
        for statement in ANALYSIS_SNAPSHOT_MIGRATION.up_statements:
            connection.exec_driver_sql(statement)
        connection.exec_driver_sql(
            """
            INSERT INTO schema_migrations (version, checksum, applied_at)
            VALUES (?, ?, ?)
            """,
            (
                ANALYSIS_SNAPSHOT_MIGRATION.version,
                ANALYSIS_SNAPSHOT_MIGRATION.checksum,
                "2026-07-10T00:00:00+00:00",
            ),
        )

    assert apply_pending_migrations(engine) == [
        ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION
    ]
    assert applied_migration_versions(engine) == [
        ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
        ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    ]
    engine.dispose()


def test_analysis_snapshot_tables_reject_update_delete_and_nonempty_rollback(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)
    apply_pending_migrations(engine)

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO analysis_runs (
                analysis_run_id, platform, language, scope_json,
                collection_run_ids_json, input_digest, template_contract_json,
                snapshot_schema_version, generation_method, source_unit_count,
                analysis_unit_count, truncated, artifact_count, output_digest,
                created_at
            ) VALUES (
                'analysis_test', 'amazon', 'zh-CN', '{}', '[]', 'sha256:input',
                '{}', 'analysis_snapshot_v1', 'deterministic_template_v1',
                0, 0, 0, 1, 'sha256:output', '2026-07-10T00:00:00+00:00'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO analysis_artifact_snapshots (
                analysis_snapshot_id, analysis_run_id, artifact_type,
                artifact_key, schema_version, payload_json, payload_digest,
                created_at
            ) VALUES (
                'snapshot_test', 'analysis_test', 'insight_brief',
                'brief:test', 'insight_brief_v1', '{"value":"one"}',
                'sha256:one', '2026-07-10T00:00:00+00:00'
            )
            """
        )

    with (
        pytest.raises(DatabaseError, match="analysis_runs_append_only"),
        engine.begin() as connection,
    ):
        connection.exec_driver_sql(
            """
            INSERT OR REPLACE INTO analysis_runs (
                analysis_run_id, platform, language, scope_json,
                collection_run_ids_json, input_digest, template_contract_json,
                snapshot_schema_version, generation_method, source_unit_count,
                analysis_unit_count, truncated, artifact_count, output_digest,
                created_at
            ) VALUES (
                'analysis_test', 'amazon', 'en-US', '{}', '[]', 'sha256:changed',
                '{}', 'analysis_snapshot_v1', 'deterministic_template_v1',
                0, 0, 0, 0, 'sha256:changed', '2026-07-10T00:00:00+00:00'
            )
            """
        )

    with (
        pytest.raises(DatabaseError, match="analysis_artifacts_append_only"),
        engine.begin() as connection,
    ):
        connection.exec_driver_sql(
            """
            INSERT OR REPLACE INTO analysis_artifact_snapshots (
                analysis_snapshot_id, analysis_run_id, artifact_type,
                artifact_key, schema_version, payload_json, payload_digest,
                created_at
            ) VALUES (
                'snapshot_test', 'analysis_test', 'insight_brief',
                'brief:test', 'insight_brief_v1', '{"value":"two"}',
                'sha256:two', '2026-07-10T00:00:00+00:00'
            )
            """
        )

    with (
        pytest.raises(DatabaseError, match="analysis_artifacts_append_only"),
        engine.begin() as connection,
    ):
        connection.exec_driver_sql(
            """
            INSERT INTO analysis_artifact_snapshots (
                analysis_snapshot_id, analysis_run_id, artifact_type,
                artifact_key, schema_version, payload_json, payload_digest,
                created_at
            ) VALUES (
                'snapshot_extra', 'analysis_test', 'strategy_note',
                'strategy:extra', 'strategy_note_v1', '{"value":"extra"}',
                'sha256:extra', '2026-07-10T00:00:00+00:00'
            )
            """
        )

    with (
        pytest.raises(DatabaseError, match="analysis_artifacts_append_only"),
        engine.begin() as connection,
    ):
        connection.exec_driver_sql(
            """
            INSERT OR REPLACE INTO analysis_artifact_snapshots (
                analysis_snapshot_id, analysis_run_id, artifact_type,
                artifact_key, schema_version, payload_json, payload_digest,
                created_at
            ) VALUES (
                'snapshot_replacement', 'analysis_test', 'insight_brief',
                'brief:test', 'insight_brief_v1', '{"value":"replacement"}',
                'sha256:replacement', '2026-07-10T00:00:00+00:00'
            )
            """
        )

    with (
        pytest.raises(DatabaseError, match="analysis_runs_append_only"),
        engine.begin() as connection,
    ):
        connection.exec_driver_sql(
            "UPDATE analysis_runs SET language = 'en-US' WHERE analysis_run_id = 'analysis_test'"
        )

    with (
        pytest.raises(DatabaseError, match="analysis_runs_append_only"),
        engine.begin() as connection,
    ):
        connection.exec_driver_sql(
            "DELETE FROM analysis_runs WHERE analysis_run_id = 'analysis_test'"
        )

    with pytest.raises(MigrationRollbackBlocked, match="analysis_snapshot_rows_exist"):
        rollback_latest_migration(engine)
    engine.dispose()


def test_migration_status_and_rollback_refuse_known_checksum_drift(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)
    apply_pending_migrations(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE schema_migrations SET checksum = 'tampered' "
            f"WHERE version = '{ANALYSIS_SNAPSHOT_MIGRATION_VERSION}'"
        )

    with pytest.raises(MigrationChecksumMismatch, match="migration_checksum_mismatch"):
        applied_migration_versions(engine)
    with pytest.raises(MigrationChecksumMismatch, match="migration_checksum_mismatch"):
        rollback_latest_migration(engine)
    with pytest.raises(MigrationChecksumMismatch, match="migration_checksum_mismatch"):
        apply_pending_migrations(engine)
    engine.dispose()


def test_migration_cli_status_does_not_enable_wal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA journal_mode=DELETE").fetchone() == ("delete",)

    monkeypatch.setenv("PLUGIN_HUB_SQLITE_WAL_ENABLED", "true")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "plugin-hub-migrate",
            "status",
            "--database-url",
            f"sqlite+pysqlite:///{database_path}",
        ],
    )

    migration_cli_main()

    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ok"
    assert result["changed_versions"] == []
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("delete",)


def test_migration_cli_status_refuses_missing_sqlite_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "missing.db"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "plugin-hub-migrate",
            "status",
            "--database-url",
            f"sqlite+pysqlite:///{database_path}",
        ],
    )

    with pytest.raises(SystemExit) as error:
        migration_cli_main()

    assert error.value.code == 2
    assert database_path.exists() is False


def test_sqlite_migration_ddl_rolls_back_as_one_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = Migration(
        version="9999_broken_probe",
        up_statements=(
            "CREATE TABLE partial_migration_probe (id INTEGER PRIMARY KEY)",
            "THIS IS NOT VALID SQL",
        ),
        down_statements=("DROP TABLE partial_migration_probe",),
    )
    original_migrations = MIGRATIONS
    original_by_version = MIGRATIONS_BY_VERSION
    monkeypatch.setattr(migration_module, "MIGRATIONS", (*original_migrations, broken))
    monkeypatch.setattr(
        migration_module,
        "MIGRATIONS_BY_VERSION",
        {**original_by_version, broken.version: broken},
    )
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)

    with pytest.raises(DatabaseError):
        apply_pending_migrations(engine)

    with engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE name = 'partial_migration_probe'"
        ).fetchone() is None
        assert connection.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE name = 'analysis_runs'"
        ).fetchone() is None
        assert connection.exec_driver_sql(
            "SELECT 1 FROM sqlite_master WHERE name = 'schema_migrations'"
        ).fetchone() is None

    monkeypatch.setattr(migration_module, "MIGRATIONS", original_migrations)
    monkeypatch.setattr(migration_module, "MIGRATIONS_BY_VERSION", original_by_version)
    assert apply_pending_migrations(engine) == [
        ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
        ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    ]
    engine.dispose()

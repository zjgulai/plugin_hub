from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.exc import DatabaseError

from plugin_hub_api.db import build_engine, init_database
from plugin_hub_api.migrations import (
    ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
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

    assert first == [ANALYSIS_SNAPSHOT_MIGRATION_VERSION]
    assert second == []
    assert applied_migration_versions(engine) == [ANALYSIS_SNAPSHOT_MIGRATION_VERSION]

    rolled_back = rollback_latest_migration(engine)

    assert rolled_back == ANALYSIS_SNAPSHOT_MIGRATION_VERSION
    assert applied_migration_versions(engine) == []
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
                0, 0, 0, 0, 'sha256:output', '2026-07-10T00:00:00+00:00'
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

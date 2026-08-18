from __future__ import annotations

import re
import sqlite3
import sys
from collections.abc import Callable, Iterable
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DatabaseError

import plugin_hub_api.migration_cli as migration_cli_module
import plugin_hub_api.migrations as migration_module
import plugin_hub_api.models  # noqa: F401
from plugin_hub_api.db import (
    MIGRATED_CORE_EVIDENCE_TABLES,
    Base,
    build_engine,
    init_database,
)
from plugin_hub_api.migration_cli import _read_migration_status
from plugin_hub_api.migrations import (
    ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION,
    ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    ANALYSIS_SNAPSHOT_MIGRATION,
    ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
    CORE_BASE_INDEX_DDL,
    CORE_EVIDENCE_BASELINE_MIGRATION_VERSION,
    CORE_EVIDENCE_IMMUTABILITY_MIGRATION,
    CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION,
    CORE_TABLE_DDL,
    CORE_TABLE_NAMES,
    CORE_UNIQUE_INDEX_DDL,
    Migration,
    MigrationContractMismatch,
    MigrationError,
    MigrationRollbackBlocked,
    applied_migration_versions,
    apply_pending_migrations,
    rollback_latest_migration,
    validate_sqlite_applied_migration_contracts,
)

ALL_VERSIONS = [
    ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
    ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    CORE_EVIDENCE_BASELINE_MIGRATION_VERSION,
    CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION,
]

CORE_TABLES = {
    "collection_runs",
    "raw_source_items",
    "canonical_voc_units",
}

CORE_UNIQUE_INDEXES = {
    "uq_raw_source_items_run_source",
    "uq_canonical_voc_units_run_source",
}

CORE_GUARDS = {
    "raw_source_items_no_update",
    "raw_source_items_no_delete",
    "raw_source_items_no_replace",
    "canonical_voc_units_no_update",
    "canonical_voc_units_no_delete",
    "canonical_voc_units_no_replace",
}


def test_legacy_snapshot_migration_checksums_remain_stable() -> None:
    assert ANALYSIS_SNAPSHOT_MIGRATION.checksum == (
        "cf0a110bb9230d49c01a9ce4f36d9f403d36ba4502a2bffd313a65773c189695"
    )
    assert ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION.checksum == (
        "6d4690f789c2ed18bd661faeea8f1216117496c77e23647cf8e213274f3288ab"
    )


def test_contract_bearing_migration_without_validator_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version = "9999_missing_contract_validator"
    migration = Migration(
        version=version,
        up_statements=(),
        down_statements=(),
        contract_payload="future-contract-v1",
    )
    monkeypatch.setitem(migration_module.MIGRATIONS_BY_VERSION, version, migration)

    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(
            MigrationContractMismatch,
            match=f"migration_contract_validator_missing:{version}",
        ):
            validate_sqlite_applied_migration_contracts(connection, [version])
    finally:
        connection.close()


def test_runtime_core_table_exclusions_match_migration_ownership() -> None:
    assert frozenset(CORE_TABLE_NAMES) == MIGRATED_CORE_EVIDENCE_TABLES


def test_break_glass_runbook_triggers_match_immutability_migration() -> None:
    repository_root = Path(__file__).parents[3]
    runbook = (
        repository_root
        / "docs/workflows/plugin-hub-core-evidence-break-glass-runbook-draft-20260809.md"
    ).read_text(encoding="utf-8")
    repair_section = runbook.split("## 4. Exact repair transaction template", 1)[1].split(
        "## 5.",
        1,
    )[0]
    runbook_statements = re.findall(
        r"CREATE TRIGGER\s+.*?\nEND;",
        repair_section,
        flags=re.DOTALL,
    )

    assert _trigger_contracts(runbook_statements) == _trigger_contracts(
        CORE_EVIDENCE_IMMUTABILITY_MIGRATION.up_statements
    )


def test_empty_database_migration_is_explicit_idempotent_and_contract_verified(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")

    assert _sqlite_names(engine, "table").isdisjoint(CORE_TABLES)
    assert apply_pending_migrations(engine) == ALL_VERSIONS
    assert apply_pending_migrations(engine) == []
    assert applied_migration_versions(engine) == ALL_VERSIONS
    assert _sqlite_names(engine, "table") >= CORE_TABLES
    assert _sqlite_names(engine, "index") >= CORE_UNIQUE_INDEXES
    assert _sqlite_names(engine, "trigger") >= CORE_GUARDS
    assert _read_migration_status(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_busy_timeout_ms=10_000,
    ) == ALL_VERSIONS
    engine.dispose()


def test_runtime_initialization_does_not_create_migrated_core_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")

    init_database(engine)

    names = _sqlite_names(engine, "table")
    assert names.isdisjoint(CORE_TABLES)
    assert {"collection_tasks", "platform_settings", "platform_setting_audit_events"} <= names
    engine.dispose()


def test_compatible_populated_legacy_schema_upgrades_without_row_drift(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _create_legacy_schema(engine)
    _insert_evidence(engine)
    before = _core_rows_digest(engine)

    assert apply_pending_migrations(engine) == ALL_VERSIONS

    assert _core_rows_digest(engine) == before
    assert _core_counts(engine) == (1, 1, 1)
    assert _sqlite_names(engine, "index") >= CORE_UNIQUE_INDEXES
    assert _sqlite_names(engine, "trigger") >= CORE_GUARDS
    engine.dispose()


@pytest.mark.parametrize(
    ("table_name", "needle", "replacement"),
    [
        (
            "collection_runs",
            "platform VARCHAR(32) NOT NULL,",
            "platform VARCHAR(32) NOT NULL CHECK (platform = 'amazon'),",
        ),
        (
            "raw_source_items",
            "PRIMARY KEY (id),",
            "PRIMARY KEY (id), UNIQUE (raw_payload_hash),",
        ),
    ],
)
def test_legacy_schema_with_unexpected_table_constraint_is_not_certified(
    tmp_path: Path,
    table_name: str,
    needle: str,
    replacement: str,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    table_statements = dict(CORE_TABLE_DDL)
    table_statements[table_name] = table_statements[table_name].replace(
        needle,
        replacement,
        1,
    )
    with engine.begin() as connection:
        for statement in table_statements.values():
            connection.exec_driver_sql(statement)
        for statement in CORE_BASE_INDEX_DDL:
            connection.exec_driver_sql(statement)

    with pytest.raises(MigrationError, match="core_evidence_schema_mismatch") as error:
        apply_pending_migrations(engine)

    assert type(error.value) is MigrationError
    assert "schema_migrations" not in _sqlite_names(engine, "table")
    assert _sqlite_names(engine, "trigger").isdisjoint(CORE_GUARDS)
    engine.dispose()


def test_legacy_schema_index_mismatch_uses_precondition_error_type(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _create_legacy_schema(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP INDEX ix_collection_runs_platform")

    with pytest.raises(MigrationError, match="core_evidence_schema_mismatch:indexes") as error:
        apply_pending_migrations(engine)

    assert type(error.value) is MigrationError
    assert "schema_migrations" not in _sqlite_names(engine, "table")
    engine.dispose()


def test_partial_core_schema_is_refused_atomically(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE collection_runs (collection_run_id TEXT PRIMARY KEY)"
        )

    with pytest.raises(MigrationError, match="core_evidence_schema_partial"):
        apply_pending_migrations(engine)

    assert "schema_migrations" not in _sqlite_names(engine, "table")
    assert "analysis_runs" not in _sqlite_names(engine, "table")
    assert _sqlite_names(engine, "table") == {"collection_runs"}
    engine.dispose()


@pytest.mark.parametrize("table_name", ["raw_source_items", "canonical_voc_units"])
def test_duplicate_run_scoped_identity_is_refused_without_identifier_leak(
    tmp_path: Path,
    table_name: str,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _create_legacy_schema(engine)
    _insert_evidence(engine)
    with engine.begin() as connection:
        if table_name == "raw_source_items":
            connection.exec_driver_sql(
                """
                INSERT INTO raw_source_items (
                    collection_run_id, platform, source_kind, source_object_id,
                    raw_schema_version, parser_version, raw_payload,
                    raw_payload_hash, captured_at
                ) VALUES (
                    'run_test', 'amazon', 'amazon_review', 'secret-object-id',
                    'amazon-review-v1', 'parser-v1', '{}', 'fnv1a64:duplicate',
                    '2026-08-09 00:00:00'
                )
                """
            )
        else:
            connection.exec_driver_sql(
                """
                INSERT INTO canonical_voc_units (
                    platform, source_kind, source_object_id, collection_run_id,
                    source_url, captured_at, body, media_refs, quality_flags,
                    coverage_confidence, platform_extension
                ) VALUES (
                    'amazon', 'amazon_review', 'secret-object-id', 'run_test',
                    'https://example.invalid/reviews', '2026-08-09 00:00:00',
                    'duplicate', '[]', '[]', 1.0, '{}'
                )
                """
            )

    with pytest.raises(
        MigrationError,
        match=rf"core_evidence_duplicate_identity:{table_name}:1",
    ) as error:
        apply_pending_migrations(engine)

    assert "secret-object-id" not in str(error.value)
    assert "schema_migrations" not in _sqlite_names(engine, "table")
    assert CORE_UNIQUE_INDEXES.isdisjoint(_sqlite_names(engine, "index"))
    engine.dispose()


@pytest.mark.parametrize(
    ("object_type", "object_name"),
    [
        ("index", "uq_raw_source_items_run_source"),
        ("trigger", "canonical_voc_units_no_update"),
    ],
)
def test_applied_contract_drift_is_refused_by_engine_and_read_only_status(
    tmp_path: Path,
    object_type: str,
    object_name: str,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    apply_pending_migrations(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(f'DROP {object_type.upper()} "{object_name}"')

    with pytest.raises(MigrationContractMismatch, match="migration_contract_mismatch"):
        applied_migration_versions(engine)
    with pytest.raises(MigrationContractMismatch, match="migration_contract_mismatch"):
        _read_migration_status(
            f"sqlite+pysqlite:///{database_path}",
            sqlite_busy_timeout_ms=10_000,
        )
    engine.dispose()


@pytest.mark.parametrize(
    ("table_name", "needle", "replacement"),
    [
        (
            "collection_runs",
            "platform VARCHAR(32) NOT NULL,",
            "platform VARCHAR(32) NOT NULL CHECK (platform = 'amazon'),",
        ),
        (
            "collection_runs",
            "platform VARCHAR(32) NOT NULL,",
            "platform TEXT NOT NULL,",
        ),
        (
            "raw_source_items",
            "FOREIGN KEY(collection_run_id) "
            "REFERENCES collection_runs (collection_run_id)",
            "FOREIGN KEY(collection_run_id) "
            "REFERENCES collection_runs (collection_run_id) ON DELETE CASCADE",
        ),
    ],
    ids=("table-definition", "column", "foreign-key"),
)
def test_applied_table_contract_drift_uses_exact_engine_and_cli_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    table_name: str,
    needle: str,
    replacement: str,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = build_engine(database_url)
    apply_pending_migrations(engine)
    _replace_core_schema_with_drift(
        engine,
        table_name=table_name,
        needle=needle,
        replacement=replacement,
    )
    expected_error = (
        "migration_contract_mismatch:"
        f"{CORE_EVIDENCE_BASELINE_MIGRATION_VERSION}"
    )

    with pytest.raises(MigrationContractMismatch) as error:
        applied_migration_versions(engine)

    assert str(error.value) == expected_error
    engine.dispose()
    monkeypatch.setattr(
        sys,
        "argv",
        ["plugin-hub-migrate", "status", "--database-url", database_url],
    )

    with pytest.raises(SystemExit) as cli_error:
        migration_cli_module.main()

    assert cli_error.value.code == 2
    stderr = capsys.readouterr().err
    assert stderr.endswith(f"plugin-hub-migrate: error: {expected_error}\n")
    assert "Traceback" not in stderr


def test_migration_cli_status_reports_contract_drift_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = build_engine(database_url)
    apply_pending_migrations(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP INDEX ix_collection_runs_platform")
    engine.dispose()
    monkeypatch.setattr(
        sys,
        "argv",
        ["plugin-hub-migrate", "status", "--database-url", database_url],
    )

    with pytest.raises(SystemExit) as error:
        migration_cli_module.main()

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert "migration_contract_mismatch:0003_core_evidence_baseline" in stderr
    assert "Traceback" not in stderr


class _NonSqliteFakeEngine:
    """Engine stand-in that forbids any connection or SQL attempt.

    Any `begin`/`connect` call proves the dialect guard did not run first,
    so these methods raise instead of returning a connection.
    """

    def __init__(self, dialect_name: str = "postgresql") -> None:
        self.dialect = SimpleNamespace(name=dialect_name)

    def begin(self) -> object:
        raise AssertionError("dialect guard must run before any connection is opened")

    def connect(self) -> object:
        raise AssertionError("dialect guard must run before any connection is opened")

    def dispose(self) -> None:
        pass


@pytest.mark.parametrize(
    "operation",
    [
        apply_pending_migrations,
        applied_migration_versions,
        rollback_latest_migration,
    ],
    ids=("apply-pending", "applied-versions", "rollback-latest"),
)
def test_public_migration_operations_refuse_non_sqlite_dialect_before_any_connection(
    operation: Callable[[Engine], object],
) -> None:
    engine = _NonSqliteFakeEngine()

    with pytest.raises(MigrationError) as error:
        operation(engine)

    assert str(error.value) == "migration_dialect_unsupported:postgresql"


def test_migration_cli_status_refuses_non_sqlite_database_url_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        migration_cli_module,
        "build_engine",
        lambda _database_url: _NonSqliteFakeEngine(),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["plugin-hub-migrate", "status", "--database-url", "postgresql://example/db"],
    )

    with pytest.raises(SystemExit) as error:
        migration_cli_module.main()

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert stderr.endswith(
        "plugin-hub-migrate: error: migration_dialect_unsupported:postgresql\n"
    )
    assert "Traceback" not in stderr


@pytest.mark.parametrize(
    "replacement_statement",
    [
        """
        CREATE UNIQUE INDEX uq_raw_source_items_run_source
        ON raw_source_items (collection_run_id, source_kind, source_object_id)
        WHERE id < 0
        """,
        """
        CREATE UNIQUE INDEX uq_raw_source_items_run_source
        ON canonical_voc_units (collection_run_id, source_kind, source_object_id)
        """,
        """
        CREATE UNIQUE INDEX uq_raw_source_items_run_source
        ON raw_source_items (
            collection_run_id COLLATE NOCASE, source_kind, source_object_id
        )
        """,
        """
        CREATE UNIQUE INDEX uq_raw_source_items_run_source
        ON raw_source_items (
            collection_run_id DESC, source_kind, source_object_id
        )
        """,
    ],
)
def test_index_contract_rejects_partial_or_wrong_table_substitute(
    tmp_path: Path,
    replacement_statement: str,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    apply_pending_migrations(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP INDEX uq_raw_source_items_run_source")
        connection.exec_driver_sql(replacement_statement)

    with pytest.raises(MigrationContractMismatch, match="migration_contract_mismatch"):
        applied_migration_versions(engine)
    with pytest.raises(MigrationContractMismatch, match="migration_contract_mismatch"):
        _read_migration_status(
            f"sqlite+pysqlite:///{database_path}",
            sqlite_busy_timeout_ms=10_000,
        )
    engine.dispose()


def test_legacy_schema_with_orphan_evidence_is_not_certified(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _create_legacy_schema(engine)
    engine.dispose()

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute(
            """
            INSERT INTO raw_source_items (
                collection_run_id, platform, source_kind, source_object_id,
                raw_schema_version, parser_version, raw_payload,
                raw_payload_hash, captured_at
            ) VALUES (
                'missing-run', 'amazon', 'amazon_review', 'orphan-object',
                'amazon-review-v1', 'parser-v1', '{}', 'fnv1a64:orphan',
                '2026-08-09 00:00:00'
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    with pytest.raises(
        MigrationError,
        match="core_evidence_orphan_evidence:raw_source_items",
    ):
        apply_pending_migrations(engine)

    assert "schema_migrations" not in _sqlite_names(engine, "table")
    engine.dispose()


def test_applied_contract_status_rejects_orphan_evidence(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    apply_pending_migrations(engine)
    engine.dispose()

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute(
            """
            INSERT INTO raw_source_items (
                collection_run_id, platform, source_kind, source_object_id,
                raw_schema_version, parser_version, raw_payload,
                raw_payload_hash, captured_at
            ) VALUES (
                'missing-run', 'amazon', 'amazon_review', 'orphan-object',
                'amazon-review-v1', 'parser-v1', '{}', 'fnv1a64:orphan',
                '2026-08-09 00:00:00'
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    with pytest.raises(
        MigrationContractMismatch,
        match="core_evidence_orphan_evidence:raw_source_items",
    ):
        applied_migration_versions(engine)
    with pytest.raises(
        MigrationContractMismatch,
        match="core_evidence_orphan_evidence:raw_source_items",
    ):
        _read_migration_status(
            f"sqlite+pysqlite:///{database_path}",
            sqlite_busy_timeout_ms=10_000,
        )
    engine.dispose()


def test_core_evidence_guards_reject_mutation_and_replacement_but_allow_append(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    apply_pending_migrations(engine)
    _insert_evidence(engine)

    _assert_database_rejects(
        engine,
        "UPDATE raw_source_items SET raw_payload_hash = 'changed' WHERE id = 1",
        "raw_source_items_append_only",
    )
    _assert_database_rejects(
        engine,
        "DELETE FROM raw_source_items WHERE id = 1",
        "raw_source_items_append_only",
    )
    _assert_database_rejects(
        engine,
        "UPDATE canonical_voc_units SET body = 'changed' WHERE id = 1",
        "canonical_voc_units_append_only",
    )
    _assert_database_rejects(
        engine,
        "DELETE FROM canonical_voc_units WHERE id = 1",
        "canonical_voc_units_append_only",
    )
    _assert_database_rejects(
        engine,
        """
        INSERT OR REPLACE INTO raw_source_items (
            id, collection_run_id, platform, source_kind, source_object_id,
            raw_schema_version, parser_version, raw_payload, raw_payload_hash,
            captured_at
        ) VALUES (
            1, 'run_test', 'amazon', 'amazon_review', 'secret-object-id',
            'amazon-review-v1', 'parser-v1', '{}', 'changed',
            '2026-08-09 00:00:00'
        )
        """,
        "raw_source_items_append_only",
    )
    _assert_database_rejects(
        engine,
        """
        INSERT OR REPLACE INTO canonical_voc_units (
            id, platform, source_kind, source_object_id, collection_run_id,
            source_url, captured_at, body, media_refs, quality_flags,
            coverage_confidence, platform_extension
        ) VALUES (
            1, 'amazon', 'amazon_review', 'secret-object-id', 'run_test',
            'https://example.invalid/reviews', '2026-08-09 00:00:00',
            'replacement', '[]', '[]', 1.0, '{}'
        )
        """,
        "canonical_voc_units_append_only",
    )

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO raw_source_items (
                collection_run_id, platform, source_kind, source_object_id,
                raw_schema_version, parser_version, raw_payload,
                raw_payload_hash, captured_at
            ) VALUES (
                'run_test', 'amazon', 'amazon_review', 'second-object',
                'amazon-review-v1', 'parser-v1', '{}', 'fnv1a64:second',
                '2026-08-09 00:00:01'
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO canonical_voc_units (
                platform, source_kind, source_object_id, collection_run_id,
                source_url, captured_at, body, media_refs, quality_flags,
                coverage_confidence, platform_extension
            ) VALUES (
                'amazon', 'amazon_review', 'second-object', 'run_test',
                'https://example.invalid/reviews', '2026-08-09 00:00:01',
                'second', '[]', '[]', 1.0, '{}'
            )
            """
        )

    assert _core_counts(engine) == (1, 2, 2)
    engine.dispose()


def test_core_migrations_roll_back_when_empty_and_block_when_populated(
    tmp_path: Path,
) -> None:
    empty_engine = build_engine(f"sqlite+pysqlite:///{tmp_path / 'empty.db'}")
    apply_pending_migrations(empty_engine)

    assert rollback_latest_migration(empty_engine) == (
        CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION
    )
    assert rollback_latest_migration(empty_engine) == CORE_EVIDENCE_BASELINE_MIGRATION_VERSION
    assert applied_migration_versions(empty_engine) == [
        ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
        ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    ]
    assert CORE_TABLES.isdisjoint(_sqlite_names(empty_engine, "table"))
    empty_engine.dispose()

    populated_engine = build_engine(f"sqlite+pysqlite:///{tmp_path / 'populated.db'}")
    apply_pending_migrations(populated_engine)
    _insert_evidence(populated_engine)
    before = _core_rows_digest(populated_engine)

    with pytest.raises(MigrationRollbackBlocked, match="core_evidence_rows_exist"):
        rollback_latest_migration(populated_engine)

    assert _core_rows_digest(populated_engine) == before
    assert _sqlite_names(populated_engine, "trigger") >= CORE_GUARDS
    populated_engine.dispose()


def test_immutability_rollback_allows_empty_children_but_baseline_keeps_parent(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite+pysqlite:///{tmp_path / 'parent-only.db'}")
    apply_pending_migrations(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO collection_runs (
                collection_run_id, platform, source_url, capture_method,
                coverage_scope, stop_reason, coverage_confidence, created_at
            ) VALUES (
                'empty-run', 'amazon', 'https://example.invalid/reviews',
                'fixture', '{}', 'complete', 1.0, '2026-08-09 00:00:00'
            )
            """
        )

    assert rollback_latest_migration(engine) == (
        CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION
    )
    with pytest.raises(MigrationRollbackBlocked, match="core_evidence_rows_exist"):
        rollback_latest_migration(engine)

    assert _core_counts(engine) == (1, 0, 0)
    assert _sqlite_names(engine, "trigger").isdisjoint(CORE_GUARDS)
    engine.dispose()


def _create_legacy_schema(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


def _replace_core_schema_with_drift(
    engine: Engine,
    *,
    table_name: str,
    needle: str,
    replacement: str,
) -> None:
    table_statements = dict(CORE_TABLE_DDL)
    original_statement = table_statements[table_name]
    table_statements[table_name] = original_statement.replace(needle, replacement, 1)
    assert table_statements[table_name] != original_statement

    with engine.begin() as connection:
        for core_table_name in reversed(CORE_TABLE_NAMES):
            connection.exec_driver_sql(f'DROP TABLE "{core_table_name}"')
        for statement in table_statements.values():
            connection.exec_driver_sql(statement)
        for statement in (*CORE_BASE_INDEX_DDL, *CORE_UNIQUE_INDEX_DDL):
            connection.exec_driver_sql(statement)
        for statement in CORE_EVIDENCE_IMMUTABILITY_MIGRATION.up_statements:
            connection.exec_driver_sql(statement)


def _insert_evidence(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO collection_runs (
                    collection_run_id, platform, source_url, capture_method,
                    coverage_scope, stop_reason, coverage_confidence, created_at
                ) VALUES (
                    'run_test', 'amazon', 'https://example.invalid/reviews',
                    'fixture', '{}', 'complete', 1.0,
                    '2026-08-09 00:00:00'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO raw_source_items (
                    collection_run_id, platform, source_kind, source_object_id,
                    raw_schema_version, parser_version, raw_payload,
                    raw_payload_hash, captured_at
                ) VALUES (
                    'run_test', 'amazon', 'amazon_review', 'secret-object-id',
                    'amazon-review-v1', 'parser-v1', '{"value":"one"}',
                    'fnv1a64:one', '2026-08-09 00:00:00'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO canonical_voc_units (
                    platform, source_kind, source_object_id, collection_run_id,
                    source_url, captured_at, body, media_refs, quality_flags,
                    coverage_confidence, platform_extension
                ) VALUES (
                    'amazon', 'amazon_review', 'secret-object-id', 'run_test',
                    'https://example.invalid/reviews', '2026-08-09 00:00:00',
                    'fixture evidence', '[]', '[]', 1.0, '{}'
                )
                """
            )
        )


def _sqlite_names(engine: Engine, object_type: str) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type = :type"),
            {"type": object_type},
        ).all()
    return {str(row[0]) for row in rows}


def _core_counts(engine: Engine) -> tuple[int, int, int]:
    with engine.connect() as connection:
        counts = tuple(
            int(connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table}"').scalar_one())
            for table in (
                "collection_runs",
                "raw_source_items",
                "canonical_voc_units",
            )
        )
    assert len(counts) == 3
    return counts


def _core_rows_digest(engine: Engine) -> str:
    rows: list[str] = []
    with engine.connect() as connection:
        for table in (
            "collection_runs",
            "raw_source_items",
            "canonical_voc_units",
        ):
            table_rows = connection.exec_driver_sql(f'SELECT * FROM "{table}" ORDER BY 1').all()
            rows.append(f"{table}:{[tuple(row) for row in table_rows]!r}")
    return sha256("\n".join(rows).encode()).hexdigest()


def _assert_database_rejects(engine: Engine, statement: str, message: str) -> None:
    with (
        pytest.raises(DatabaseError, match=message),
        engine.begin() as connection,
    ):
        connection.exec_driver_sql(statement)


def _trigger_contracts(statements: Iterable[str]) -> dict[str, str]:
    contracts: dict[str, str] = {}
    for statement in statements:
        match = re.search(r"CREATE TRIGGER\s+([a-z0-9_]+)", statement)
        assert match is not None
        contracts[match.group(1)] = " ".join(statement.split()).rstrip(";")
    return contracts

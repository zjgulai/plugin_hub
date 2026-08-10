from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

ANALYSIS_SNAPSHOT_MIGRATION_VERSION = "0001_analysis_snapshots"
ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION = (
    "0002_analysis_snapshot_insert_guards"
)
CORE_EVIDENCE_BASELINE_MIGRATION_VERSION = "0003_core_evidence_baseline"
CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION = "0004_core_evidence_immutability"

CORE_EVIDENCE_SCHEMA_MISMATCH_CODE = "core_evidence_schema_mismatch"
CORE_EVIDENCE_INDEX_MISMATCH_CODE = "core_evidence_schema_mismatch:indexes"
CORE_EVIDENCE_ORPHAN_CODE = "core_evidence_orphan_evidence"
MIGRATION_CONTRACT_MISMATCH_CODE = "migration_contract_mismatch"
MIGRATION_CONTRACT_VALIDATOR_MISSING_CODE = "migration_contract_validator_missing"

_TABLE_SCOPED_CORE_EVIDENCE_ERROR_CODES = frozenset(
    {
        CORE_EVIDENCE_SCHEMA_MISMATCH_CODE,
        CORE_EVIDENCE_ORPHAN_CODE,
    }
)


class MigrationError(RuntimeError):
    pass


class MigrationChecksumMismatch(MigrationError):
    pass


class MigrationRollbackBlocked(MigrationError):
    pass


class MigrationContractMismatch(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    up_statements: tuple[str, ...]
    down_statements: tuple[str, ...]
    contract_payload: str | None = None

    @property
    def checksum(self) -> str:
        payload = "\n-- statement --\n".join(self.up_statements)
        if self.contract_payload is not None:
            payload = f"{payload}\n-- contract --\n{self.contract_payload}"
        return sha256(payload.encode("utf-8")).hexdigest()


MIGRATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
)
"""

ANALYSIS_SNAPSHOT_MIGRATION = Migration(
    version=ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
    up_statements=(
        """
        CREATE TABLE analysis_runs (
            analysis_run_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL CHECK (platform IN ('amazon', 'reddit')),
            language TEXT NOT NULL,
            scope_json TEXT NOT NULL CHECK (json_valid(scope_json)),
            collection_run_ids_json TEXT NOT NULL CHECK (json_valid(collection_run_ids_json)),
            input_digest TEXT NOT NULL,
            template_contract_json TEXT NOT NULL CHECK (json_valid(template_contract_json)),
            snapshot_schema_version TEXT NOT NULL,
            generation_method TEXT NOT NULL,
            source_unit_count INTEGER NOT NULL CHECK (source_unit_count >= 0),
            analysis_unit_count INTEGER NOT NULL CHECK (analysis_unit_count >= 0),
            truncated INTEGER NOT NULL CHECK (truncated IN (0, 1)),
            artifact_count INTEGER NOT NULL CHECK (artifact_count >= 0),
            output_digest TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE analysis_artifact_snapshots (
            analysis_snapshot_id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL CHECK (
                artifact_type IN (
                    'relation_edge',
                    'enriched_voc_signal',
                    'strategy_note',
                    'insight_brief'
                )
            ),
            artifact_key TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
            payload_digest TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (analysis_run_id)
                REFERENCES analysis_runs(analysis_run_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,
            UNIQUE (analysis_run_id, artifact_type, artifact_key)
        )
        """,
        """
        CREATE INDEX ix_analysis_runs_platform_created_at
        ON analysis_runs(platform, created_at DESC)
        """,
        """
        CREATE INDEX ix_analysis_artifacts_run_type
        ON analysis_artifact_snapshots(analysis_run_id, artifact_type)
        """,
        """
        CREATE TRIGGER analysis_runs_no_update
        BEFORE UPDATE ON analysis_runs
        BEGIN
            SELECT RAISE(ABORT, 'analysis_runs_append_only');
        END
        """,
        """
        CREATE TRIGGER analysis_runs_no_delete
        BEFORE DELETE ON analysis_runs
        BEGIN
            SELECT RAISE(ABORT, 'analysis_runs_append_only');
        END
        """,
        """
        CREATE TRIGGER analysis_artifacts_no_update
        BEFORE UPDATE ON analysis_artifact_snapshots
        BEGIN
            SELECT RAISE(ABORT, 'analysis_artifacts_append_only');
        END
        """,
        """
        CREATE TRIGGER analysis_artifacts_no_delete
        BEFORE DELETE ON analysis_artifact_snapshots
        BEGIN
            SELECT RAISE(ABORT, 'analysis_artifacts_append_only');
        END
        """,
    ),
    down_statements=(
        "DROP TRIGGER IF EXISTS analysis_artifacts_no_delete",
        "DROP TRIGGER IF EXISTS analysis_artifacts_no_update",
        "DROP TRIGGER IF EXISTS analysis_runs_no_delete",
        "DROP TRIGGER IF EXISTS analysis_runs_no_update",
        "DROP INDEX IF EXISTS ix_analysis_artifacts_run_type",
        "DROP INDEX IF EXISTS ix_analysis_runs_platform_created_at",
        "DROP TABLE IF EXISTS analysis_artifact_snapshots",
        "DROP TABLE IF EXISTS analysis_runs",
    ),
)

ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION = Migration(
    version=ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    up_statements=(
        """
        CREATE TRIGGER analysis_runs_no_replace
        BEFORE INSERT ON analysis_runs
        WHEN EXISTS (
            SELECT 1 FROM analysis_runs
            WHERE analysis_run_id = NEW.analysis_run_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'analysis_runs_append_only');
        END
        """,
        """
        CREATE TRIGGER analysis_artifacts_no_replace
        BEFORE INSERT ON analysis_artifact_snapshots
        WHEN EXISTS (
            SELECT 1 FROM analysis_artifact_snapshots
            WHERE analysis_snapshot_id = NEW.analysis_snapshot_id
               OR (
                    analysis_run_id = NEW.analysis_run_id
                    AND artifact_type = NEW.artifact_type
                    AND artifact_key = NEW.artifact_key
               )
        )
        OR (
            SELECT COUNT(*)
            FROM analysis_artifact_snapshots
            WHERE analysis_run_id = NEW.analysis_run_id
        ) >= (
            SELECT artifact_count
            FROM analysis_runs
            WHERE analysis_run_id = NEW.analysis_run_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'analysis_artifacts_append_only');
        END
        """,
    ),
    down_statements=(
        "DROP TRIGGER IF EXISTS analysis_artifacts_no_replace",
        "DROP TRIGGER IF EXISTS analysis_runs_no_replace",
    ),
)

CORE_EVIDENCE_BASELINE_CONTRACT = """
core-evidence-schema-v1
tables:
  collection_runs(collection_run_id,platform,source_url,capture_method,coverage_scope,
    stop_reason,coverage_confidence,created_at)
  raw_source_items(id,collection_run_id,platform,source_kind,source_object_id,
    raw_schema_version,parser_version,raw_payload,raw_payload_hash,captured_at)
  canonical_voc_units(id,platform,source_kind,source_object_id,collection_run_id,
    source_url,captured_at,created_at,author_display,author_type,title,body,language,
    media_refs,commercial_object_type,brand,product_title,asin,parent_asin,marketplace,
    category,thread_id,parent_id,depth,reply_role,quality_flags,coverage_confidence,
    platform_extension)
foreign-keys:
  raw_source_items.collection_run_id->collection_runs.collection_run_id
  canonical_voc_units.collection_run_id->collection_runs.collection_run_id
unique-identities:
  raw_source_items(collection_run_id,source_kind,source_object_id)
  canonical_voc_units(collection_run_id,source_kind,source_object_id)
""".strip()

CORE_TABLE_DDL = {
    "collection_runs": """
        CREATE TABLE IF NOT EXISTS collection_runs (
            collection_run_id VARCHAR(64) NOT NULL,
            platform VARCHAR(32) NOT NULL,
            source_url TEXT NOT NULL,
            capture_method VARCHAR(128) NOT NULL,
            coverage_scope JSON NOT NULL,
            stop_reason VARCHAR(128),
            coverage_confidence FLOAT NOT NULL,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (collection_run_id)
        )
        """,
    "raw_source_items": """
        CREATE TABLE IF NOT EXISTS raw_source_items (
            id INTEGER NOT NULL,
            collection_run_id VARCHAR(64) NOT NULL,
            platform VARCHAR(32) NOT NULL,
            source_kind VARCHAR(64) NOT NULL,
            source_object_id VARCHAR(256) NOT NULL,
            raw_schema_version VARCHAR(128) NOT NULL,
            parser_version VARCHAR(128) NOT NULL,
            raw_payload JSON NOT NULL,
            raw_payload_hash VARCHAR(256) NOT NULL,
            captured_at DATETIME NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(collection_run_id) REFERENCES collection_runs (collection_run_id)
        )
        """,
    "canonical_voc_units": """
        CREATE TABLE IF NOT EXISTS canonical_voc_units (
            id INTEGER NOT NULL,
            platform VARCHAR(32) NOT NULL,
            source_kind VARCHAR(64) NOT NULL,
            source_object_id VARCHAR(256) NOT NULL,
            collection_run_id VARCHAR(64) NOT NULL,
            source_url TEXT NOT NULL,
            captured_at DATETIME NOT NULL,
            created_at DATETIME,
            author_display VARCHAR(256),
            author_type VARCHAR(128),
            title TEXT,
            body TEXT NOT NULL,
            language VARCHAR(32),
            media_refs JSON NOT NULL,
            commercial_object_type VARCHAR(128),
            brand VARCHAR(256),
            product_title TEXT,
            asin VARCHAR(32),
            parent_asin VARCHAR(32),
            marketplace VARCHAR(32),
            category VARCHAR(256),
            thread_id VARCHAR(256),
            parent_id VARCHAR(256),
            depth INTEGER,
            reply_role VARCHAR(64),
            quality_flags JSON NOT NULL,
            coverage_confidence FLOAT NOT NULL,
            platform_extension JSON NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(collection_run_id) REFERENCES collection_runs (collection_run_id)
        )
        """,
}

CORE_BASE_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS ix_collection_runs_platform "
    "ON collection_runs (platform)",
    "CREATE INDEX IF NOT EXISTS ix_raw_source_items_collection_run_id "
    "ON raw_source_items (collection_run_id)",
    "CREATE INDEX IF NOT EXISTS ix_raw_source_items_platform "
    "ON raw_source_items (platform)",
    "CREATE INDEX IF NOT EXISTS ix_canonical_voc_units_collection_run_id "
    "ON canonical_voc_units (collection_run_id)",
    "CREATE INDEX IF NOT EXISTS ix_canonical_voc_units_platform "
    "ON canonical_voc_units (platform)",
    "CREATE INDEX IF NOT EXISTS ix_canonical_voc_units_thread_id "
    "ON canonical_voc_units (thread_id)",
)

CORE_UNIQUE_INDEX_DDL = (
    "CREATE UNIQUE INDEX uq_raw_source_items_run_source "
    "ON raw_source_items (collection_run_id, source_kind, source_object_id)",
    "CREATE UNIQUE INDEX uq_canonical_voc_units_run_source "
    "ON canonical_voc_units (collection_run_id, source_kind, source_object_id)",
)

CORE_EVIDENCE_BASELINE_MIGRATION = Migration(
    version=CORE_EVIDENCE_BASELINE_MIGRATION_VERSION,
    up_statements=(
        *CORE_TABLE_DDL.values(),
        *CORE_BASE_INDEX_DDL,
        *CORE_UNIQUE_INDEX_DDL,
    ),
    down_statements=(
        "DROP TABLE IF EXISTS canonical_voc_units",
        "DROP TABLE IF EXISTS raw_source_items",
        "DROP TABLE IF EXISTS collection_runs",
    ),
    contract_payload=CORE_EVIDENCE_BASELINE_CONTRACT,
)

CORE_EVIDENCE_IMMUTABILITY_CONTRACT = """
core-evidence-immutability-v1
raw_source_items: no_update,no_delete,no_replace
canonical_voc_units: no_update,no_delete,no_replace
""".strip()

CORE_EVIDENCE_IMMUTABILITY_MIGRATION = Migration(
    version=CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION,
    up_statements=(
        """
        CREATE TRIGGER raw_source_items_no_update
        BEFORE UPDATE ON raw_source_items
        BEGIN
            SELECT RAISE(ABORT, 'raw_source_items_append_only');
        END
        """,
        """
        CREATE TRIGGER raw_source_items_no_delete
        BEFORE DELETE ON raw_source_items
        BEGIN
            SELECT RAISE(ABORT, 'raw_source_items_append_only');
        END
        """,
        """
        CREATE TRIGGER raw_source_items_no_replace
        BEFORE INSERT ON raw_source_items
        WHEN EXISTS (
            SELECT 1 FROM raw_source_items
            WHERE id = NEW.id
               OR (
                    collection_run_id = NEW.collection_run_id
                    AND source_kind = NEW.source_kind
                    AND source_object_id = NEW.source_object_id
               )
        )
        BEGIN
            SELECT RAISE(ABORT, 'raw_source_items_append_only');
        END
        """,
        """
        CREATE TRIGGER canonical_voc_units_no_update
        BEFORE UPDATE ON canonical_voc_units
        BEGIN
            SELECT RAISE(ABORT, 'canonical_voc_units_append_only');
        END
        """,
        """
        CREATE TRIGGER canonical_voc_units_no_delete
        BEFORE DELETE ON canonical_voc_units
        BEGIN
            SELECT RAISE(ABORT, 'canonical_voc_units_append_only');
        END
        """,
        """
        CREATE TRIGGER canonical_voc_units_no_replace
        BEFORE INSERT ON canonical_voc_units
        WHEN EXISTS (
            SELECT 1 FROM canonical_voc_units
            WHERE id = NEW.id
               OR (
                    collection_run_id = NEW.collection_run_id
                    AND source_kind = NEW.source_kind
                    AND source_object_id = NEW.source_object_id
               )
        )
        BEGIN
            SELECT RAISE(ABORT, 'canonical_voc_units_append_only');
        END
        """,
    ),
    down_statements=(
        "DROP TRIGGER IF EXISTS canonical_voc_units_no_replace",
        "DROP TRIGGER IF EXISTS canonical_voc_units_no_delete",
        "DROP TRIGGER IF EXISTS canonical_voc_units_no_update",
        "DROP TRIGGER IF EXISTS raw_source_items_no_replace",
        "DROP TRIGGER IF EXISTS raw_source_items_no_delete",
        "DROP TRIGGER IF EXISTS raw_source_items_no_update",
    ),
    contract_payload=CORE_EVIDENCE_IMMUTABILITY_CONTRACT,
)

MIGRATIONS: tuple[Migration, ...] = (
    ANALYSIS_SNAPSHOT_MIGRATION,
    ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION,
    CORE_EVIDENCE_BASELINE_MIGRATION,
    CORE_EVIDENCE_IMMUTABILITY_MIGRATION,
)
MIGRATIONS_BY_VERSION = {migration.version: migration for migration in MIGRATIONS}

SqliteQuery = Callable[[str], list[tuple[object, ...]]]

CORE_TABLE_NAMES = tuple(CORE_TABLE_DDL)

CORE_TABLE_COLUMNS: dict[str, tuple[tuple[str, str, int, int], ...]] = {
    "collection_runs": (
        ("collection_run_id", "VARCHAR(64)", 1, 1),
        ("platform", "VARCHAR(32)", 1, 0),
        ("source_url", "TEXT", 1, 0),
        ("capture_method", "VARCHAR(128)", 1, 0),
        ("coverage_scope", "JSON", 1, 0),
        ("stop_reason", "VARCHAR(128)", 0, 0),
        ("coverage_confidence", "FLOAT", 1, 0),
        ("created_at", "DATETIME", 1, 0),
    ),
    "raw_source_items": (
        ("id", "INTEGER", 1, 1),
        ("collection_run_id", "VARCHAR(64)", 1, 0),
        ("platform", "VARCHAR(32)", 1, 0),
        ("source_kind", "VARCHAR(64)", 1, 0),
        ("source_object_id", "VARCHAR(256)", 1, 0),
        ("raw_schema_version", "VARCHAR(128)", 1, 0),
        ("parser_version", "VARCHAR(128)", 1, 0),
        ("raw_payload", "JSON", 1, 0),
        ("raw_payload_hash", "VARCHAR(256)", 1, 0),
        ("captured_at", "DATETIME", 1, 0),
    ),
    "canonical_voc_units": (
        ("id", "INTEGER", 1, 1),
        ("platform", "VARCHAR(32)", 1, 0),
        ("source_kind", "VARCHAR(64)", 1, 0),
        ("source_object_id", "VARCHAR(256)", 1, 0),
        ("collection_run_id", "VARCHAR(64)", 1, 0),
        ("source_url", "TEXT", 1, 0),
        ("captured_at", "DATETIME", 1, 0),
        ("created_at", "DATETIME", 0, 0),
        ("author_display", "VARCHAR(256)", 0, 0),
        ("author_type", "VARCHAR(128)", 0, 0),
        ("title", "TEXT", 0, 0),
        ("body", "TEXT", 1, 0),
        ("language", "VARCHAR(32)", 0, 0),
        ("media_refs", "JSON", 1, 0),
        ("commercial_object_type", "VARCHAR(128)", 0, 0),
        ("brand", "VARCHAR(256)", 0, 0),
        ("product_title", "TEXT", 0, 0),
        ("asin", "VARCHAR(32)", 0, 0),
        ("parent_asin", "VARCHAR(32)", 0, 0),
        ("marketplace", "VARCHAR(32)", 0, 0),
        ("category", "VARCHAR(256)", 0, 0),
        ("thread_id", "VARCHAR(256)", 0, 0),
        ("parent_id", "VARCHAR(256)", 0, 0),
        ("depth", "INTEGER", 0, 0),
        ("reply_role", "VARCHAR(64)", 0, 0),
        ("quality_flags", "JSON", 1, 0),
        ("coverage_confidence", "FLOAT", 1, 0),
        ("platform_extension", "JSON", 1, 0),
    ),
}

IndexColumnContract = tuple[str, bool, str]
IndexContract = tuple[str, bool, str, bool, tuple[IndexColumnContract, ...]]


def _ascending_binary_columns(*column_names: str) -> tuple[IndexColumnContract, ...]:
    return tuple((column_name, False, "BINARY") for column_name in column_names)

CORE_BASE_INDEXES: dict[str, IndexContract] = {
    "ix_collection_runs_platform": (
        "collection_runs",
        False,
        "c",
        False,
        _ascending_binary_columns("platform"),
    ),
    "ix_raw_source_items_collection_run_id": (
        "raw_source_items",
        False,
        "c",
        False,
        _ascending_binary_columns("collection_run_id"),
    ),
    "ix_raw_source_items_platform": (
        "raw_source_items",
        False,
        "c",
        False,
        _ascending_binary_columns("platform"),
    ),
    "ix_canonical_voc_units_collection_run_id": (
        "canonical_voc_units",
        False,
        "c",
        False,
        _ascending_binary_columns("collection_run_id"),
    ),
    "ix_canonical_voc_units_platform": (
        "canonical_voc_units",
        False,
        "c",
        False,
        _ascending_binary_columns("platform"),
    ),
    "ix_canonical_voc_units_thread_id": (
        "canonical_voc_units",
        False,
        "c",
        False,
        _ascending_binary_columns("thread_id"),
    ),
}

CORE_UNIQUE_INDEXES: dict[str, IndexContract] = {
    "uq_raw_source_items_run_source": (
        "raw_source_items",
        True,
        "c",
        False,
        _ascending_binary_columns(
            "collection_run_id", "source_kind", "source_object_id"
        ),
    ),
    "uq_canonical_voc_units_run_source": (
        "canonical_voc_units",
        True,
        "c",
        False,
        _ascending_binary_columns(
            "collection_run_id", "source_kind", "source_object_id"
        ),
    ),
}

CORE_GUARD_NAMES = (
    "raw_source_items_no_update",
    "raw_source_items_no_delete",
    "raw_source_items_no_replace",
    "canonical_voc_units_no_update",
    "canonical_voc_units_no_delete",
    "canonical_voc_units_no_replace",
)


def apply_pending_migrations(engine: Engine) -> list[str]:
    applied_now: list[str] = []
    with engine.begin() as connection:
        _begin_sqlite_ddl_transaction(connection)
        connection.exec_driver_sql(MIGRATION_TABLE_SQL)
        applied = _applied_migration_checksums(connection)
        _validate_known_migrations(applied)
        for migration in MIGRATIONS:
            applied_checksum = applied.get(migration.version)
            if applied_checksum is not None:
                _validate_migration_contract(connection, migration)
                continue
            _validate_migration_preconditions(connection, migration)
            for statement in migration.up_statements:
                connection.exec_driver_sql(statement)
            _validate_migration_contract(connection, migration)
            connection.execute(
                text(
                    """
                    INSERT INTO schema_migrations (version, checksum, applied_at)
                    VALUES (:version, :checksum, :applied_at)
                    """
                ),
                {
                    "version": migration.version,
                    "checksum": migration.checksum,
                    "applied_at": datetime.now(tz=UTC).isoformat(),
                },
            )
            applied_now.append(migration.version)
    return applied_now


def applied_migration_versions(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        if not _table_exists(connection, "schema_migrations"):
            return []
        applied = _applied_migration_checksums(connection)
        versions = migration_versions_from_applied_checksums(applied)
        _validate_applied_migration_contracts(connection, versions)
        return versions


def rollback_latest_migration(engine: Engine) -> str | None:
    with engine.begin() as connection:
        _begin_sqlite_ddl_transaction(connection)
        if not _table_exists(connection, "schema_migrations"):
            return None
        applied = _applied_migration_checksums(connection)
        _validate_known_migrations(applied)
        versions = [migration.version for migration in MIGRATIONS if migration.version in applied]
        if not versions:
            return None
        _validate_applied_migration_contracts(connection, versions)
        version = versions[-1]
        migration = MIGRATIONS_BY_VERSION[version]
        if version in {
            ANALYSIS_SNAPSHOT_MIGRATION_VERSION,
            ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
        } and (
            _table_count(connection, "analysis_runs") > 0
            or _table_count(connection, "analysis_artifact_snapshots") > 0
        ):
            raise MigrationRollbackBlocked("analysis_snapshot_rows_exist")
        if version == CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION and any(
            _table_count(connection, table_name) > 0
            for table_name in ("raw_source_items", "canonical_voc_units")
        ):
            raise MigrationRollbackBlocked("core_evidence_rows_exist")
        if version == CORE_EVIDENCE_BASELINE_MIGRATION_VERSION and any(
            _table_count(connection, table_name) > 0 for table_name in CORE_TABLE_NAMES
        ):
            raise MigrationRollbackBlocked("core_evidence_rows_exist")
        for statement in migration.down_statements:
            connection.exec_driver_sql(statement)
        connection.execute(
            text("DELETE FROM schema_migrations WHERE version = :version"),
            {"version": version},
        )
        return version


def _applied_migration_checksums(connection: Connection) -> dict[str, str]:
    rows = connection.execute(
        text("SELECT version, checksum FROM schema_migrations ORDER BY version")
    ).all()
    return {str(row[0]): str(row[1]) for row in rows}


def _validate_known_migrations(applied: dict[str, str]) -> None:
    unknown = sorted(set(applied) - set(MIGRATIONS_BY_VERSION))
    if unknown:
        raise MigrationError(f"unknown_migration_versions:{','.join(unknown)}")
    for version, checksum in applied.items():
        if checksum != MIGRATIONS_BY_VERSION[version].checksum:
            raise MigrationChecksumMismatch(f"migration_checksum_mismatch:{version}")


def migration_versions_from_applied_checksums(applied: dict[str, str]) -> list[str]:
    _validate_known_migrations(applied)
    return [migration.version for migration in MIGRATIONS if migration.version in applied]


def migration_contract_versions(applied_versions: Sequence[str]) -> list[str]:
    return [
        version
        for version in applied_versions
        if MIGRATIONS_BY_VERSION[version].contract_payload is not None
    ]


def validate_sqlite_applied_migration_contracts(
    connection: sqlite3.Connection,
    applied_versions: Sequence[str],
) -> None:
    def query(statement: str) -> list[tuple[object, ...]]:
        return [tuple(row) for row in connection.execute(statement).fetchall()]

    _validate_applied_contracts_with_query(query, applied_versions)


def _validate_migration_preconditions(connection: Connection, migration: Migration) -> None:
    query = _connection_query(connection)
    if migration.version == CORE_EVIDENCE_BASELINE_MIGRATION_VERSION:
        present = {
            table_name
            for table_name in CORE_TABLE_NAMES
            if _query_table_exists(query, table_name)
        }
        if present and present != set(CORE_TABLE_NAMES):
            raise MigrationError("core_evidence_schema_partial")
        if present:
            _validate_core_tables(
                query,
                error_code=CORE_EVIDENCE_SCHEMA_MISMATCH_CODE,
                error_type=MigrationError,
            )
            _validate_core_indexes(
                query,
                expected=CORE_BASE_INDEXES,
                error_code=CORE_EVIDENCE_INDEX_MISMATCH_CODE,
                error_type=MigrationError,
            )
            _refuse_duplicate_core_identities(query)
    elif migration.version == CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION:
        _validate_core_baseline_contract(
            query,
            error_code=(
                f"{MIGRATION_CONTRACT_MISMATCH_CODE}:"
                f"{CORE_EVIDENCE_BASELINE_MIGRATION_VERSION}"
            ),
        )


def _validate_migration_contract(connection: Connection, migration: Migration) -> None:
    _validate_contract_for_version(_connection_query(connection), migration.version)


def _validate_applied_migration_contracts(
    connection: Connection,
    applied_versions: Sequence[str],
) -> None:
    _validate_applied_contracts_with_query(_connection_query(connection), applied_versions)


def _validate_applied_contracts_with_query(
    query: SqliteQuery,
    applied_versions: Sequence[str],
) -> None:
    for version in migration_contract_versions(applied_versions):
        _validate_contract_for_version(query, version)


def _validate_contract_for_version(query: SqliteQuery, version: str) -> None:
    migration = MIGRATIONS_BY_VERSION[version]
    if migration.contract_payload is None:
        return
    error_code = f"{MIGRATION_CONTRACT_MISMATCH_CODE}:{version}"
    if version == CORE_EVIDENCE_BASELINE_MIGRATION_VERSION:
        _validate_core_baseline_contract(query, error_code=error_code)
    elif version == CORE_EVIDENCE_IMMUTABILITY_MIGRATION_VERSION:
        _validate_core_baseline_contract(
            query,
            error_code=(
                f"{MIGRATION_CONTRACT_MISMATCH_CODE}:"
                f"{CORE_EVIDENCE_BASELINE_MIGRATION_VERSION}"
            ),
        )
        _validate_core_guards(query, error_code=error_code)
    else:
        raise MigrationContractMismatch(
            f"{MIGRATION_CONTRACT_VALIDATOR_MISSING_CODE}:{version}"
        )


def _validate_core_baseline_contract(query: SqliteQuery, *, error_code: str) -> None:
    if any(not _query_table_exists(query, table_name) for table_name in CORE_TABLE_NAMES):
        raise MigrationContractMismatch(error_code)
    _validate_core_tables(
        query,
        error_code=error_code,
        error_type=MigrationContractMismatch,
    )
    _validate_core_indexes(
        query,
        expected={**CORE_BASE_INDEXES, **CORE_UNIQUE_INDEXES},
        error_code=error_code,
        error_type=MigrationContractMismatch,
    )


def _validate_core_tables(
    query: SqliteQuery,
    *,
    error_code: str,
    error_type: type[MigrationError],
) -> None:
    for table_name, expected_columns in CORE_TABLE_COLUMNS.items():
        expected_statement = CORE_TABLE_DDL[table_name]
        definition_rows = query(
            "SELECT sql FROM sqlite_master "
            f"WHERE type = 'table' AND name = '{table_name}'"
        )
        if len(definition_rows) != 1 or _normalize_table_sql(
            str(definition_rows[0][0])
        ) != _normalize_table_sql(expected_statement):
            _raise_contract_mismatch(
                error_code,
                error_type=error_type,
                detail=table_name,
            )

        column_rows = query(f'PRAGMA table_info("{table_name}")')
        actual_columns = tuple(
            (
                str(row[1]),
                str(row[2]).upper(),
                cast(int, row[3]),
                cast(int, row[5]),
            )
            for row in column_rows
        )
        if actual_columns != expected_columns:
            _raise_contract_mismatch(
                error_code,
                error_type=error_type,
                detail=table_name,
            )

        foreign_key_rows = query(f'PRAGMA foreign_key_list("{table_name}")')
        actual_foreign_keys = tuple(
            (str(row[2]), str(row[3]), str(row[4]), str(row[5]), str(row[6]))
            for row in foreign_key_rows
        )
        expected_foreign_keys: tuple[tuple[str, str, str, str, str], ...]
        if table_name == "collection_runs":
            expected_foreign_keys = ()
        else:
            expected_foreign_keys = (
                (
                    "collection_runs",
                    "collection_run_id",
                    "collection_run_id",
                    "NO ACTION",
                    "NO ACTION",
                ),
            )
        if actual_foreign_keys != expected_foreign_keys:
            _raise_contract_mismatch(
                error_code,
                error_type=error_type,
                detail=table_name,
            )
        if foreign_key_rows and query(f'PRAGMA foreign_key_check("{table_name}")'):
            _raise_contract_mismatch(
                CORE_EVIDENCE_ORPHAN_CODE,
                error_type=error_type,
                detail=table_name,
            )


def _validate_core_indexes(
    query: SqliteQuery,
    *,
    expected: dict[str, IndexContract],
    error_code: str,
    error_type: type[MigrationError],
) -> None:
    actual: dict[str, IndexContract] = {}
    for table_name in CORE_TABLE_NAMES:
        for row in query(f'PRAGMA index_list("{table_name}")'):
            index_name = str(row[1])
            origin = str(row[3])
            if index_name.startswith("sqlite_autoindex_") and origin == "pk":
                continue
            columns = tuple(
                (str(column[2]), bool(column[3]), str(column[4]).upper())
                for column in query(f'PRAGMA index_xinfo("{index_name}")')
                if bool(column[5])
            )
            actual[index_name] = (
                table_name,
                bool(row[2]),
                origin,
                bool(row[4]),
                columns,
            )
    if actual != expected:
        _raise_contract_mismatch(error_code, error_type=error_type)


def _validate_core_guards(query: SqliteQuery, *, error_code: str) -> None:
    rows = query(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'trigger'
          AND tbl_name IN ('raw_source_items', 'canonical_voc_units')
        ORDER BY name
        """
    )
    actual = {str(name): _normalize_sql(str(sql)) for name, sql in rows}
    expected = {
        name: _normalize_sql(statement)
        for name, statement in zip(
            CORE_GUARD_NAMES,
            CORE_EVIDENCE_IMMUTABILITY_MIGRATION.up_statements,
            strict=True,
        )
    }
    if actual != expected:
        raise MigrationContractMismatch(error_code)


def _refuse_duplicate_core_identities(query: SqliteQuery) -> None:
    for table_name in ("raw_source_items", "canonical_voc_units"):
        rows = query(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT 1
                FROM "{table_name}"
                GROUP BY collection_run_id, source_kind, source_object_id
                HAVING COUNT(*) > 1
            ) AS duplicate_groups
            """
        )
        duplicate_group_count = cast(int, rows[0][0])
        if duplicate_group_count:
            raise MigrationError(
                "core_evidence_duplicate_identity:"
                f"{table_name}:{duplicate_group_count}"
            )


def _connection_query(connection: Connection) -> SqliteQuery:
    def query(statement: str) -> list[tuple[object, ...]]:
        return [tuple(row) for row in connection.exec_driver_sql(statement).all()]

    return query


def _query_table_exists(query: SqliteQuery, table_name: str) -> bool:
    rows = query(
        "SELECT 1 FROM sqlite_master "
        f"WHERE type = 'table' AND name = '{table_name}'"
    )
    return bool(rows)


def _normalize_sql(statement: str) -> str:
    return " ".join(statement.split()).rstrip(";")


def _normalize_table_sql(statement: str) -> str:
    return _normalize_sql(statement).replace(
        "CREATE TABLE IF NOT EXISTS ",
        "CREATE TABLE ",
        1,
    )


def _raise_contract_mismatch(
    error_code: str,
    *,
    error_type: type[MigrationError],
    detail: str | None = None,
) -> None:
    if detail is not None and error_code in _TABLE_SCOPED_CORE_EVIDENCE_ERROR_CODES:
        error_code = f"{error_code}:{detail}"
    raise error_type(error_code)


def _begin_sqlite_ddl_transaction(connection: Connection) -> None:
    if connection.dialect.name == "sqlite":
        # Python's sqlite3 legacy transaction mode does not begin a transaction
        # for DDL. An explicit BEGIN makes the entire migration rollback-safe.
        connection.exec_driver_sql("BEGIN IMMEDIATE")


def _table_exists(connection: Connection, table_name: str) -> bool:
    value = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": table_name},
    ).scalar_one_or_none()
    return value is not None


def _table_count(connection: Connection, table_name: str) -> int:
    return int(connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"').scalar_one())

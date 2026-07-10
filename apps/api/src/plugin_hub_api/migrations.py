from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

ANALYSIS_SNAPSHOT_MIGRATION_VERSION = "0001_analysis_snapshots"


class MigrationError(RuntimeError):
    pass


class MigrationChecksumMismatch(MigrationError):
    pass


class MigrationRollbackBlocked(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    up_statements: tuple[str, ...]
    down_statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        payload = "\n-- statement --\n".join(self.up_statements)
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

MIGRATIONS: tuple[Migration, ...] = (ANALYSIS_SNAPSHOT_MIGRATION,)
MIGRATIONS_BY_VERSION = {migration.version: migration for migration in MIGRATIONS}


def apply_pending_migrations(engine: Engine) -> list[str]:
    applied_now: list[str] = []
    with engine.begin() as connection:
        connection.exec_driver_sql(MIGRATION_TABLE_SQL)
        applied = _applied_migration_checksums(connection)
        _validate_known_migrations(applied)
        for migration in MIGRATIONS:
            applied_checksum = applied.get(migration.version)
            if applied_checksum is not None:
                if applied_checksum != migration.checksum:
                    raise MigrationChecksumMismatch(
                        f"migration_checksum_mismatch:{migration.version}"
                    )
                continue
            for statement in migration.up_statements:
                connection.exec_driver_sql(statement)
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
        _validate_known_migrations(applied)
        return [migration.version for migration in MIGRATIONS if migration.version in applied]


def rollback_latest_migration(engine: Engine) -> str | None:
    with engine.begin() as connection:
        if not _table_exists(connection, "schema_migrations"):
            return None
        applied = _applied_migration_checksums(connection)
        _validate_known_migrations(applied)
        versions = [migration.version for migration in MIGRATIONS if migration.version in applied]
        if not versions:
            return None
        version = versions[-1]
        migration = MIGRATIONS_BY_VERSION[version]
        if version == ANALYSIS_SNAPSHOT_MIGRATION_VERSION and (
            _table_count(connection, "analysis_runs") > 0
            or _table_count(connection, "analysis_artifact_snapshots") > 0
        ):
            raise MigrationRollbackBlocked("analysis_snapshot_rows_exist")
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


def _table_exists(connection: Connection, table_name: str) -> bool:
    value = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
        {"name": table_name},
    ).scalar_one_or_none()
    return value is not None


def _table_count(connection: Connection, table_name: str) -> int:
    return int(connection.exec_driver_sql(f'SELECT COUNT(*) FROM "{table_name}"').scalar_one())

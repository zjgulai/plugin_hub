from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool


class Base(DeclarativeBase):
    pass


MIGRATED_CORE_EVIDENCE_TABLES = frozenset(
    {
        "collection_runs",
        "raw_source_items",
        "canonical_voc_units",
    }
)


def build_engine(
    database_url: str,
    *,
    sqlite_busy_timeout_ms: int = 10_000,
    sqlite_wal_enabled: bool = False,
) -> Engine:
    if database_url == "sqlite+pysqlite:///:memory:":
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    elif database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={
                "check_same_thread": False,
                "timeout": sqlite_busy_timeout_ms / 1_000,
            },
        )
    else:
        return create_engine(database_url)

    _configure_sqlite_connections(
        engine,
        busy_timeout_ms=sqlite_busy_timeout_ms,
        wal_enabled=sqlite_wal_enabled,
    )
    return engine


def _configure_sqlite_connections(
    engine: Engine,
    *,
    busy_timeout_ms: int,
    wal_enabled: bool,
) -> None:
    def set_pragmas(
        dbapi_connection: DBAPIConnection,
        _connection_record: ConnectionPoolEntry,
    ) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms:d}")
            if wal_enabled:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=FULL")
        finally:
            cursor.close()

    event.listen(engine, "connect", set_pragmas)


def make_session_factory(engine: Engine) -> Callable[[], Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    operational_tables = [
        table
        for table in Base.metadata.sorted_tables
        if table.name not in MIGRATED_CORE_EVIDENCE_TABLES
    ]
    Base.metadata.create_all(bind=engine, tables=operational_tables)
    _restrict_sqlite_file_permissions(engine)


def _restrict_sqlite_file_permissions(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    database = engine.url.database
    if database is None or database == ":memory:":
        return

    database_path = Path(database).resolve()
    for candidate in (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ):
        if candidate.exists():
            candidate.chmod(0o600)

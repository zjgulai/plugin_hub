from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from stat import S_IMODE
from threading import Barrier

from sqlalchemy import text

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.schemas import CollectionRun, RawSourceItem
from plugin_hub_api.services.collection_runs import map_raw_item_to_voc
from plugin_hub_api.worker_cli import build_worker_engine


def test_sqlite_file_connections_enforce_foreign_keys_and_busy_timeout(tmp_path: Path) -> None:
    database_path = tmp_path / "durability.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)

    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()

    assert foreign_keys == 1
    assert busy_timeout >= 10_000
    assert S_IMODE(database_path.stat().st_mode) == 0o600
    engine.dispose()


def test_sqlite_wal_serializes_concurrent_atomic_collection_writes(tmp_path: Path) -> None:
    database_path = tmp_path / "concurrent.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_busy_timeout_ms=10_000,
        sqlite_wal_enabled=True,
    )
    init_database(engine)
    session_factory = make_session_factory(engine)
    writer_count = 8
    start_barrier = Barrier(writer_count)

    def save_collection(index: int) -> None:
        run = CollectionRun.model_validate(
            {
                "collection_run_id": f"run_concurrent_{index}",
                "platform": "amazon",
                "source_url": "https://www.amazon.com/product-reviews/B000000001",
                "capture_method": "concurrency_test",
                "coverage_scope": {"writer": index},
                "coverage_confidence": 0.8,
                "created_at": datetime(2026, 7, 10, tzinfo=UTC),
            }
        )
        raw_item = RawSourceItem.model_validate(
            {
                "platform": "amazon",
                "source_kind": "amazon_review",
                "source_object_id": f"R_CONCURRENT_{index}",
                "raw_schema_version": "amazon-review-v1",
                "parser_version": "parser-v1",
                "raw_payload": {
                    "review_id": f"R_CONCURRENT_{index}",
                    "body": f"Concurrent evidence {index}",
                },
                "raw_payload_hash": f"sha256:concurrent-{index}",
                "captured_at": datetime(2026, 7, 10, tzinfo=UTC),
            }
        )
        voc_unit = map_raw_item_to_voc(run=run, raw_item=raw_item)
        start_barrier.wait()
        with session_factory() as session:
            SqlAlchemyRepository(session).save_collection(
                run=run,
                raw_items=[raw_item],
                voc_units=[voc_unit],
            )

    with ThreadPoolExecutor(max_workers=writer_count) as executor:
        list(executor.map(save_collection, range(writer_count)))

    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"
        assert connection.execute(text("PRAGMA quick_check")).scalar_one() == "ok"
        assert connection.execute(text("SELECT COUNT(*) FROM collection_runs")).scalar_one() == 8
        assert connection.execute(text("SELECT COUNT(*) FROM raw_source_items")).scalar_one() == 8
        assert (
            connection.execute(text("SELECT COUNT(*) FROM canonical_voc_units")).scalar_one()
            == 8
        )
        assert (
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM raw_source_items AS item
                    LEFT JOIN collection_runs AS run
                      ON run.collection_run_id = item.collection_run_id
                    WHERE run.collection_run_id IS NULL
                    """
                )
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM canonical_voc_units AS item
                    LEFT JOIN collection_runs AS run
                      ON run.collection_run_id = item.collection_run_id
                    WHERE run.collection_run_id IS NULL
                    """
                )
            ).scalar_one()
            == 0
        )

    for sqlite_path in (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ):
        if sqlite_path.exists():
            assert S_IMODE(sqlite_path.stat().st_mode) == 0o600

    engine.dispose()


def test_worker_engine_honors_sqlite_durability_settings(tmp_path: Path) -> None:
    database_path = tmp_path / "worker.db"
    settings = Settings(
        sqlite_busy_timeout_ms=23_000,
        sqlite_wal_enabled=True,
    )
    engine = build_worker_engine(
        settings,
        f"sqlite+pysqlite:///{database_path}",
    )

    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"
        assert connection.execute(text("PRAGMA synchronous")).scalar_one() == 2
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 23_000

    engine.dispose()

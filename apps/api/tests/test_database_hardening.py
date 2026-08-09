from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from stat import S_IMODE
from threading import Barrier

import pytest
from sqlalchemy import text

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.repositories import CollectionTaskClaimLostError, SqlAlchemyRepository
from plugin_hub_api.routes.collection_tasks import (
    list_collection_tasks as list_collection_tasks_route,
)
from plugin_hub_api.schemas import (
    CollectionRun,
    CollectionTask,
    CollectionTaskStatus,
    Platform,
    RawSourceItem,
)
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


def test_sqlite_collection_task_claim_is_atomic_across_workers(tmp_path: Path) -> None:
    database_path = tmp_path / "atomic-claim.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_busy_timeout_ms=10_000,
        sqlite_wal_enabled=True,
    )
    init_database(engine)
    session_factory = make_session_factory(engine)
    now = datetime(2026, 7, 28, tzinfo=UTC)
    task = CollectionTask.model_validate(
        {
            "collection_task_id": "task_atomic_claim",
            "platform": "reddit",
            "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
            "requested_capture_method": "server_reddit_json_proxy",
            "trigger_reason": "concurrency_test",
            "context": {"thread_id": "thread123"},
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
    )
    with session_factory() as session:
        SqlAlchemyRepository(session).save_collection_task(task)

    worker_count = 8
    start_barrier = Barrier(worker_count)

    def claim(index: int) -> str | None:
        start_barrier.wait()
        with session_factory() as session:
            claimed = SqlAlchemyRepository(session).claim_next_runnable_collection_task(
                worker_id=f"worker-{index}",
                claim_ttl_seconds=600,
                now=now,
            )
            return claimed.context["claimed_by"] if claimed is not None else None

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        claims = list(executor.map(claim, range(worker_count)))

    assert len([claim for claim in claims if claim is not None]) == 1
    with session_factory() as session:
        stored = SqlAlchemyRepository(session).get_collection_task(task.collection_task_id)
    assert stored is not None
    assert stored.status.value == "running"
    assert stored.context["claimed_by"] in claims
    engine.dispose()


def test_expired_worker_claim_cannot_commit_collection_evidence(tmp_path: Path) -> None:
    database_path = tmp_path / "claim-fence.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_busy_timeout_ms=10_000,
        sqlite_wal_enabled=True,
    )
    init_database(engine)
    session_factory = make_session_factory(engine)
    now = datetime(2026, 7, 28, tzinfo=UTC)
    task = CollectionTask.model_validate(
        {
            "collection_task_id": "task_claim_fence",
            "platform": "amazon",
            "source_url": "https://www.amazon.com/product-reviews/B000000001",
            "requested_capture_method": "server_amazon_capture",
            "trigger_reason": "claim_fence_test",
            "context": {},
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
    )
    with session_factory() as session:
        SqlAlchemyRepository(session).save_collection_task(task)
    with session_factory() as session:
        first_claim = SqlAlchemyRepository(session).claim_collection_task(
            collection_task_id=task.collection_task_id,
            worker_id="worker-a",
            claim_ttl_seconds=1,
            now=now,
        )
    with session_factory() as session:
        second_claim = SqlAlchemyRepository(session).claim_collection_task(
            collection_task_id=task.collection_task_id,
            worker_id="worker-b",
            claim_ttl_seconds=600,
            now=now + timedelta(seconds=2),
        )
    assert first_claim is not None
    assert second_claim is not None
    first_claim_token = first_claim.context["claim_token"]
    assert isinstance(first_claim_token, str)

    run = CollectionRun.model_validate(
        {
            "collection_run_id": "run_stale_worker",
            "platform": "amazon",
            "source_url": "https://www.amazon.com/product-reviews/B000000001",
            "capture_method": "claim_fence_test",
            "coverage_scope": {"worker": "worker-a"},
            "coverage_confidence": 1.0,
            "created_at": now + timedelta(seconds=3),
        }
    )
    raw_item = RawSourceItem.model_validate(
        {
            "platform": "amazon",
            "source_kind": "amazon_review",
            "source_object_id": "R_STALE_WORKER",
            "raw_schema_version": "amazon-review-v1",
            "parser_version": "parser-v1",
            "raw_payload": {
                "review_id": "R_STALE_WORKER",
                "body": "Stale worker evidence must not commit.",
            },
            "raw_payload_hash": "sha256:stale-worker",
            "captured_at": now + timedelta(seconds=3),
        }
    )
    completed_task = first_claim.model_copy(
        update={
            "status": CollectionTaskStatus.COMPLETED,
            "updated_at": now + timedelta(seconds=3),
            "context": {
                **first_claim.context,
                "collection_run_id": run.collection_run_id,
                "claim_token": None,
            },
        }
    )
    with session_factory() as session:
        repository = SqlAlchemyRepository(session)
        with pytest.raises(CollectionTaskClaimLostError, match="collection_task_claim_lost"):
            repository.save_collection_and_update_task(
                run=run,
                raw_items=[raw_item],
                voc_units=[map_raw_item_to_voc(run=run, raw_item=raw_item)],
                task=completed_task,
                expected_claim_token=first_claim_token,
                now=now + timedelta(seconds=3),
            )

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM collection_runs")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM raw_source_items")).scalar_one() == 0
        assert (
            connection.execute(text("SELECT COUNT(*) FROM canonical_voc_units")).scalar_one()
            == 0
        )
    with session_factory() as session:
        stored = SqlAlchemyRepository(session).get_collection_task(task.collection_task_id)
    assert stored is not None
    assert stored.status == CollectionTaskStatus.RUNNING
    assert stored.context["claimed_by"] == "worker-b"
    assert stored.context["claim_token"] == second_claim.context["claim_token"]
    engine.dispose()


def test_collection_task_list_uses_one_snapshot_during_concurrent_transition(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "task-list-snapshot.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_busy_timeout_ms=10_000,
        sqlite_wal_enabled=True,
    )
    init_database(engine)
    session_factory = make_session_factory(engine)
    now = datetime(2026, 7, 28, tzinfo=UTC)
    task = CollectionTask.model_validate(
        {
            "collection_task_id": "task_snapshot_consistency",
            "platform": "reddit",
            "source_url": "https://www.reddit.com/r/test/comments/thread/example/",
            "requested_capture_method": "server_reddit_json_proxy",
            "trigger_reason": "snapshot_consistency_test",
            "context": {"thread_id": "thread"},
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
    )
    with session_factory() as session:
        SqlAlchemyRepository(session).save_collection_task(task)

    class ConcurrentTransitionRepository(SqlAlchemyRepository):
        transitioned = False

        def count_collection_tasks(
            self,
            *,
            platform: Platform | None = None,
            statuses: tuple[CollectionTaskStatus, ...] | None = None,
        ) -> int:
            count = super().count_collection_tasks(platform=platform, statuses=statuses)
            if not self.transitioned:
                self.transitioned = True
                with session_factory() as writer_session:
                    writer_repository = SqlAlchemyRepository(writer_session)
                    stored = writer_repository.get_collection_task(task.collection_task_id)
                    assert stored is not None
                    writer_repository.update_collection_task(
                        stored.model_copy(
                            update={
                                "status": CollectionTaskStatus.COMPLETED,
                                "updated_at": now + timedelta(seconds=1),
                            }
                        )
                    )
            return count

    with session_factory() as session:
        response = list_collection_tasks_route(
            repository=ConcurrentTransitionRepository(session),
            platform=None,
            limit=100,
            offset=0,
        )

    assert response.total == 1
    assert response.open_total == 1
    assert response.open_totals[task.platform] == 1
    assert response.items[0].status == CollectionTaskStatus.PENDING
    with session_factory() as session:
        stored = SqlAlchemyRepository(session).get_collection_task(task.collection_task_id)
    assert stored is not None
    assert stored.status == CollectionTaskStatus.COMPLETED
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

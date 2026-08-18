from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.migrations import apply_pending_migrations
from plugin_hub_api.payload_hashes import fnv1a64_payload_hash
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.data_assets import list_data_asset_runs
from plugin_hub_api.schemas import DataAssetRun, JsonValue


def _init_migrated_database(engine: Engine) -> None:
    init_database(engine)
    apply_pending_migrations(engine)


def test_data_asset_summary_reports_durable_counts_without_payloads(client: TestClient) -> None:
    raw_payload: dict[str, JsonValue] = {
        "review_id": "R123",
        "body": "Durable evidence.",
        "captured_at": "2026-06-05T00:00:00+00:00",
    }
    response = client.post(
        "/api/collection-runs",
        json={
            "run": {
                "platform": "amazon",
                "source_url": "https://www.amazon.com/product-reviews/B000000001",
                "capture_method": "browser_extension",
                "coverage_scope": {"page": 1},
                "stop_reason": "manual_stop",
                "coverage_confidence": 0.8,
            },
            "raw_items": [
                {
                    "platform": "amazon",
                    "source_kind": "amazon_review",
                    "source_object_id": "R123",
                    "raw_schema_version": "amazon-review-v1",
                    "parser_version": "parser-v1",
                    "raw_payload": raw_payload,
                    "raw_payload_hash": fnv1a64_payload_hash(raw_payload),
                    "captured_at": "2026-06-05T00:00:00+00:00",
                }
            ],
        },
    )
    assert response.status_code == 201

    summary_response = client.get("/api/data-assets/summary")

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert {
        key: value
        for key, value in summary.items()
        if key not in {"latest_run_at", "latest_capture_at"}
    } == {
        "collection_run_count": 1,
        "raw_item_count": 1,
        "canonical_voc_count": 1,
        "analysis_eligible_voc_count": 1,
        "placeholder_voc_count": 0,
        "flagged_voc_count": 0,
        "low_confidence_voc_count": 0,
        "average_coverage_confidence": 0.8,
        "runs_with_count_mismatch": 0,
        "orphan_raw_count": 0,
        "orphan_voc_count": 0,
        "platform_counts": {"amazon": 1, "instagram": 0, "reddit": 0},
    }
    assert summary["latest_run_at"] is not None
    assert summary["latest_capture_at"] == "2026-06-05T00:00:00"
    serialized = str(summary).lower()
    assert "raw_payload" not in serialized
    assert "body" not in serialized

    runs_response = client.get("/api/data-assets/runs")
    assert runs_response.status_code == 200
    runs = runs_response.json()
    assert runs["total"] == 1
    assert runs["items"] == [
        {
            "collection_run_id": response.json()["collection_run_id"],
            "platform": "amazon",
            "capture_method": "browser_extension",
            "stop_reason": "manual_stop",
            "coverage_confidence": 0.8,
            "created_at": summary["latest_run_at"],
            "first_captured_at": "2026-06-05T00:00:00",
            "last_captured_at": "2026-06-05T00:00:00",
            "raw_item_count": 1,
            "canonical_voc_count": 1,
            "analysis_eligible_voc_count": 1,
            "placeholder_voc_count": 0,
            "asset_state": "complete",
        }
    ]
    assert "source_url" not in str(runs).lower()


def test_begin_read_snapshot_refuses_existing_transaction_without_rollback(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _init_migrated_database(engine)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO collection_runs (
                    collection_run_id, platform, source_url, capture_method,
                    coverage_scope, stop_reason, coverage_confidence, created_at
                ) VALUES (
                    'run-existing-transaction', 'amazon',
                    'https://www.amazon.com/product-reviews/B000000001', 'test',
                    '{}', NULL, 1.0, '2026-07-30T00:00:00+00:00'
                )
                """
            )
        )
        repository = SqlAlchemyRepository(session)

        with pytest.raises(RuntimeError, match="read_snapshot_requires_clean_session"):
            repository.begin_read_snapshot()

        assert session.in_transaction()
        assert session.scalar(text("SELECT COUNT(*) FROM collection_runs")) == 1

    engine.dispose()


def test_data_asset_runs_route_ends_read_snapshot(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _init_migrated_database(engine)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        response = list_data_asset_runs(
            SqlAlchemyRepository(session),
            limit=50,
            offset=0,
        )

        assert response.total == 0
        assert not session.in_transaction()

    engine.dispose()


def test_data_asset_summary_ends_read_snapshot_after_error(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _init_migrated_database(engine)
    session_factory = make_session_factory(engine)

    class FailingSummaryRepository(SqlAlchemyRepository):
        def _text_count(self, statement: str) -> int:
            raise RuntimeError("summary_probe_failed")

    with session_factory() as session:
        repository = FailingSummaryRepository(session)

        with pytest.raises(RuntimeError, match="summary_probe_failed"):
            repository.get_data_asset_summary(low_confidence_threshold=0.7)

        assert not session.in_transaction()

    engine.dispose()


def test_data_asset_runs_route_ends_read_snapshot_after_error(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    _init_migrated_database(engine)
    session_factory = make_session_factory(engine)

    class FailingRunsRepository(SqlAlchemyRepository):
        def list_data_asset_runs(self, *, limit: int, offset: int) -> list[DataAssetRun]:
            raise RuntimeError("runs_probe_failed")

    with session_factory() as session:
        repository = FailingRunsRepository(session)

        with pytest.raises(RuntimeError, match="runs_probe_failed"):
            list_data_asset_runs(repository, limit=50, offset=0)

        assert not session.in_transaction()

    engine.dispose()


def test_data_asset_summary_uses_one_snapshot_during_concurrent_insert(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_wal_enabled=True,
    )
    _init_migrated_database(engine)
    session_factory = make_session_factory(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO collection_runs (
                    collection_run_id, platform, source_url, capture_method,
                    coverage_scope, stop_reason, coverage_confidence, created_at
                ) VALUES (
                    'run-concurrent-summary', 'reddit',
                    'https://www.reddit.com/r/test/comments/thread/', 'test',
                    '{}', NULL, 1.0, '2026-07-28T00:00:00+00:00'
                )
                """
            )
        )

    class ConcurrentInsertRepository(SqlAlchemyRepository):
        def __init__(self, session: Session) -> None:
            super().__init__(session)
            self.inserted = False

        def _text_count(self, statement: str) -> int:
            if not self.inserted:
                self.inserted = True
                with engine.begin() as writer:
                    writer.execute(
                        text(
                            """
                            INSERT INTO canonical_voc_units (
                                platform, source_kind, source_object_id,
                                collection_run_id, source_url, captured_at, body,
                                media_refs, quality_flags, coverage_confidence,
                                platform_extension
                            ) VALUES (
                                'reddit', 'reddit_comment', 'placeholder-late',
                                'run-concurrent-summary',
                                'https://www.reddit.com/r/test/comments/thread/',
                                '2026-07-28T00:00:00+00:00', '', '[]',
                                '["reddit_more_node"]', 1.0, '{}'
                            )
                            """
                        )
                    )
            return super()._text_count(statement)

    with session_factory() as session:
        summary = ConcurrentInsertRepository(session).get_data_asset_summary(
            low_confidence_threshold=0.7
        )
        assert not session.in_transaction()

    assert summary.canonical_voc_count == 0
    assert summary.placeholder_voc_count == 0
    assert summary.analysis_eligible_voc_count == 0
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT COUNT(*) FROM canonical_voc_units")).scalar_one() == 1
        )
    engine.dispose()

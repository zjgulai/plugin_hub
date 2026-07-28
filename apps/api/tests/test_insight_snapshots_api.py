from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DatabaseError

from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.insight_snapshot_repository import InsightSnapshotRepository
from plugin_hub_api.migrations import MigrationRollbackBlocked, apply_pending_migrations
from plugin_hub_api.payload_hashes import fnv1a64_payload_hash
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.insights import (
    AnalysisSnapshotCreateRequest,
    bounded_analysis_units,
    create_analysis_snapshot,
)
from plugin_hub_api.schemas import CanonicalVocUnit, JsonValue, Platform


def test_insight_endpoints_reject_unsupported_language_metadata(client: TestClient) -> None:
    snapshot_response = client.post(
        "/api/insights/snapshots",
        json={"platform": "amazon", "language": "en-US"},
    )
    briefs_response = client.get(
        "/api/insights/briefs",
        params={"platform": "amazon", "language": "en-US"},
    )

    assert snapshot_response.status_code == 422
    assert briefs_response.status_code == 422


def test_snapshot_endpoint_requires_explicit_migration(client: TestClient) -> None:
    response = client.post(
        "/api/insights/snapshots",
        json={"platform": "amazon", "language": "zh-CN"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "analysis_snapshot_schema_not_ready"


def test_snapshot_preserves_run_lineage_for_repeated_source_object(
    client: TestClient,
) -> None:
    apply_pending_migrations(client.app.state.engine)
    collection_run_ids: list[str] = []
    for index in (1, 2):
        raw_payload: dict[str, JsonValue] = {
            "review_id": "repeated-review-1",
            "rating": 2,
            "body": "The product broke after two weeks.",
            "asin": "B000000001",
            "captured_at": "2026-07-10T00:00:00+00:00",
        }
        response = client.post(
            "/api/collection-runs",
            json={
                "run": {
                    "platform": "amazon",
                    "source_url": "https://www.amazon.com/product-reviews/B000000001",
                    "capture_method": "browser_extension",
                    "coverage_scope": {"page": index},
                    "stop_reason": "manual_stop",
                    "coverage_confidence": 0.9,
                },
                "raw_items": [
                    {
                        "platform": "amazon",
                        "source_kind": "amazon_review",
                        "source_object_id": "repeated-review-1",
                        "raw_schema_version": "amazon-review-v1",
                        "parser_version": "parser-v1",
                        "raw_payload": raw_payload,
                        "raw_payload_hash": fnv1a64_payload_hash(raw_payload),
                        "captured_at": "2026-07-10T00:00:00+00:00",
                    }
                ],
            },
        )
        assert response.status_code == 201
        collection_run_ids.append(response.json()["collection_run_id"])

    snapshot_response = client.post(
        "/api/insights/snapshots",
        json={"platform": "amazon", "language": "zh-CN"},
    )

    assert snapshot_response.status_code == 201
    analysis_run_id = snapshot_response.json()["run"]["analysis_run_id"]
    detail = client.get(f"/api/insights/snapshots/{analysis_run_id}").json()
    relation_artifacts = [
        artifact
        for artifact in detail["artifacts"]
        if artifact["artifact_type"] == "relation_edge"
    ]
    assert len(relation_artifacts) == 2
    assert {artifact["payload"]["collection_run_id"] for artifact in relation_artifacts} == set(
        collection_run_ids
    )
    assert len({artifact["artifact_key"] for artifact in relation_artifacts}) == 2


def test_snapshot_creation_is_append_only_idempotent_and_queryable(client: TestClient) -> None:
    apply_pending_migrations(client.app.state.engine)
    raw_payload: dict[str, JsonValue] = {
        "review_id": "snapshot-review-1",
        "rating": 2,
        "title": "Breaks too quickly",
        "body": "The product broke after two weeks.",
        "asin": "B000000001",
        "captured_at": "2026-07-10T00:00:00+00:00",
    }
    collection_response = client.post(
        "/api/collection-runs",
        json={
            "run": {
                "platform": "amazon",
                "source_url": "https://www.amazon.com/product-reviews/B000000001",
                "capture_method": "browser_extension",
                "coverage_scope": {"page": 1},
                "stop_reason": "manual_stop",
                "coverage_confidence": 0.9,
            },
            "raw_items": [
                {
                    "platform": "amazon",
                    "source_kind": "amazon_review",
                    "source_object_id": "snapshot-review-1",
                    "raw_schema_version": "amazon-review-v1",
                    "parser_version": "parser-v1",
                    "raw_payload": raw_payload,
                    "raw_payload_hash": fnv1a64_payload_hash(raw_payload),
                    "captured_at": datetime(2026, 7, 10, tzinfo=UTC).isoformat(),
                }
            ],
        },
    )
    assert collection_response.status_code == 201
    collection_run_id = collection_response.json()["collection_run_id"]

    first = client.post(
        "/api/insights/snapshots",
        json={"platform": "amazon", "language": "zh-CN"},
    )
    second = client.post(
        "/api/insights/snapshots",
        json={"platform": "amazon", "language": "zh-CN"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_body = first.json()
    second_body = second.json()
    assert first_body["replayed"] is False
    assert second_body["replayed"] is True
    assert second_body["run"] == first_body["run"]
    assert first_body["run"]["platform"] == "amazon"
    assert first_body["run"]["language"] == "zh-CN"
    assert first_body["run"]["snapshot_schema_version"] == "analysis_snapshot_v1"
    assert first_body["run"]["collection_run_ids"] == [collection_run_id]
    assert first_body["run"]["source_unit_count"] == 1
    assert first_body["run"]["analysis_unit_count"] == 1
    assert first_body["run"]["artifact_count"] >= 4

    analysis_run_id = first_body["run"]["analysis_run_id"]
    listing = client.get("/api/insights/snapshots", params={"platform": "amazon"})
    detail = client.get(f"/api/insights/snapshots/{analysis_run_id}")

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"] == [first_body["run"]]
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["run"] == first_body["run"]
    artifact_types = {item["artifact_type"] for item in detail_body["artifacts"]}
    assert artifact_types == {
        "relation_edge",
        "enriched_voc_signal",
        "strategy_note",
        "insight_brief",
    }
    assert all(item["payload_digest"].startswith("sha256:") for item in detail_body["artifacts"])

    with (
        pytest.raises(DatabaseError, match="analysis_artifacts_append_only"),
        client.app.state.engine.begin() as connection,
    ):
        connection.exec_driver_sql("UPDATE analysis_artifact_snapshots SET schema_version = 'v2'")

    with pytest.raises(MigrationRollbackBlocked, match="analysis_snapshot_rows_exist"):
        from plugin_hub_api.migrations import rollback_latest_migration

        rollback_latest_migration(client.app.state.engine)


def test_analysis_count_and_units_share_one_sqlite_read_snapshot(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_wal_enabled=True,
    )
    init_database(engine)
    session_factory = make_session_factory(engine)
    with engine.begin() as connection:
        _insert_collection_run(connection, "run-old")
        _insert_collection_run(connection, "run-new")
        _insert_voc_unit(connection, "run-old", "old-evidence", quality_flags="[]")

    with session_factory() as reader_session:
        repository = SqlAlchemyRepository(reader_session)
        repository.begin_read_snapshot()
        source_unit_count = repository.count_voc_units(platform=Platform.AMAZON)

        with engine.begin() as writer_connection:
            _insert_voc_unit(writer_connection, "run-new", "new-evidence", quality_flags="[]")

        units = repository.list_voc_units(
            platform=Platform.AMAZON,
            limit=2_000,
            newest_first=True,
            exclude_quality_flag="reddit_more_node",
        )

    assert source_unit_count == 1
    assert [unit.source_object_id for unit in units] == ["old-evidence"]
    engine.dispose()


def test_snapshot_history_items_and_total_share_one_sqlite_read_snapshot(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_wal_enabled=True,
    )
    init_database(engine)
    apply_pending_migrations(engine)
    with engine.begin() as connection:
        _insert_analysis_run(connection, "analysis-old", "2026-07-28T00:00:00+00:00")

    concurrent_inserted = False

    def insert_after_page_query(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        nonlocal concurrent_inserted
        if concurrent_inserted or "ORDER BY created_at DESC" not in statement:
            return
        concurrent_inserted = True
        with engine.begin() as writer:
            _insert_analysis_run(writer, "analysis-new", "2026-07-28T01:00:00+00:00")

    event.listen(engine, "after_cursor_execute", insert_after_page_query)
    try:
        session_factory = make_session_factory(engine)
        with session_factory() as session:
            items, total = InsightSnapshotRepository(session).list_runs(
                platform=Platform.AMAZON,
                limit=50,
                offset=0,
            )
    finally:
        event.remove(engine, "after_cursor_execute", insert_after_page_query)

    assert concurrent_inserted is True
    assert total == 1
    assert [item.analysis_run_id for item in items] == ["analysis-old"]
    engine.dispose()


def test_snapshot_history_listing_preserves_caller_transaction(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)
    apply_pending_migrations(engine)
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        _insert_analysis_run(
            session.connection(),
            "analysis-uncommitted",
            "2026-07-28T00:00:00+00:00",
        )
        items, total = InsightSnapshotRepository(session).list_runs(
            platform=Platform.AMAZON,
            limit=50,
            offset=0,
        )

        assert session.in_transaction() is True
        assert total == 1
        assert [item.analysis_run_id for item in items] == ["analysis-uncommitted"]
        session.rollback()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM analysis_runs")).scalar_one() == 0
    engine.dispose()


def test_snapshot_persistence_uses_fresh_transaction_after_concurrent_commit(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(
        f"sqlite+pysqlite:///{database_path}",
        sqlite_wal_enabled=True,
    )
    init_database(engine)
    apply_pending_migrations(engine)
    session_factory = make_session_factory(engine)
    with engine.begin() as connection:
        _insert_collection_run(connection, "run-old")
        _insert_collection_run(connection, "run-new")
        _insert_voc_unit(connection, "run-old", "old-evidence", quality_flags="[]")

    class ConcurrentWriteRepository(SqlAlchemyRepository):
        inserted = False

        def list_voc_units(
            self,
            *,
            platform: Platform | None = None,
            limit: int | None = None,
            offset: int = 0,
            newest_first: bool = False,
            snapshot_max_id: int | None = None,
            exclude_quality_flag: str | None = None,
        ) -> list[CanonicalVocUnit]:
            units = super().list_voc_units(
                platform=platform,
                limit=limit,
                offset=offset,
                newest_first=newest_first,
                snapshot_max_id=snapshot_max_id,
                exclude_quality_flag=exclude_quality_flag,
            )
            if not self.inserted:
                self.inserted = True
                with engine.begin() as writer:
                    _insert_voc_unit(
                        writer,
                        "run-new",
                        "new-evidence",
                        quality_flags="[]",
                    )
            return units

    with session_factory() as session:
        response = create_analysis_snapshot(
            AnalysisSnapshotCreateRequest(platform=Platform.AMAZON),
            ConcurrentWriteRepository(session),
            InsightSnapshotRepository(session),
        )

    assert response.replayed is False
    assert response.run.source_unit_count == 1
    assert response.run.analysis_unit_count == 1
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM analysis_runs")).scalar_one() == 1
    engine.dispose()


def test_analysis_filters_placeholders_before_applying_source_limit(tmp_path: Path) -> None:
    database_path = tmp_path / "plugin_hub.db"
    engine = build_engine(f"sqlite+pysqlite:///{database_path}")
    init_database(engine)
    session_factory = make_session_factory(engine)
    with engine.begin() as connection:
        _insert_collection_run(connection, "run-reddit", platform="reddit")
        _insert_voc_unit(
            connection,
            "run-reddit",
            "valid-old-evidence",
            platform="reddit",
            source_kind="reddit_comment",
            quality_flags="[]",
        )
        connection.execute(
            text(
                """
                INSERT INTO canonical_voc_units (
                    platform, source_kind, source_object_id, collection_run_id,
                    source_url, captured_at, body, media_refs, quality_flags,
                    coverage_confidence, platform_extension
                ) VALUES (
                    'reddit', 'reddit_comment', :source_object_id, 'run-reddit',
                    'https://www.reddit.com/r/test/comments/thread/',
                    '2026-07-28T00:00:00+00:00', '', '[]',
                    '["reddit_more_node"]', 1.0, '{}'
                )
                """
            ),
            [
                {"source_object_id": f"placeholder-{index}"}
                for index in range(2_000)
            ],
        )

    with session_factory() as session:
        units, source_unit_count = bounded_analysis_units(
            SqlAlchemyRepository(session),
            Platform.REDDIT,
        )

    assert source_unit_count == 1
    assert [unit.source_object_id for unit in units] == ["valid-old-evidence"]
    engine.dispose()


def _insert_collection_run(
    connection: Connection,
    run_id: str,
    *,
    platform: str = "amazon",
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO collection_runs (
                collection_run_id, platform, source_url, capture_method,
                coverage_scope, stop_reason, coverage_confidence, created_at
            ) VALUES (
                :run_id, :platform, :source_url, 'test', '{}', NULL, 1.0,
                '2026-07-28T00:00:00+00:00'
            )
            """
        ),
        {
            "run_id": run_id,
            "platform": platform,
            "source_url": (
                "https://www.amazon.com/product-reviews/B000000001"
                if platform == "amazon"
                else "https://www.reddit.com/r/test/comments/thread/"
            ),
        },
    )


def _insert_voc_unit(
    connection: Connection,
    run_id: str,
    source_object_id: str,
    *,
    platform: str = "amazon",
    source_kind: str = "amazon_review",
    quality_flags: str,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO canonical_voc_units (
                platform, source_kind, source_object_id, collection_run_id,
                source_url, captured_at, body, media_refs, quality_flags,
                coverage_confidence, platform_extension
            ) VALUES (
                :platform, :source_kind, :source_object_id, :run_id,
                :source_url, '2026-07-28T00:00:00+00:00', 'Evidence',
                '[]', :quality_flags, 1.0, '{}'
            )
            """
        ),
        {
            "platform": platform,
            "source_kind": source_kind,
            "source_object_id": source_object_id,
            "run_id": run_id,
            "source_url": (
                "https://www.amazon.com/product-reviews/B000000001"
                if platform == "amazon"
                else "https://www.reddit.com/r/test/comments/thread/"
            ),
            "quality_flags": quality_flags,
        },
    )


def _insert_analysis_run(
    connection: Connection,
    analysis_run_id: str,
    created_at: str,
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO analysis_runs (
                analysis_run_id, platform, language, scope_json,
                collection_run_ids_json, input_digest, template_contract_json,
                snapshot_schema_version, generation_method, source_unit_count,
                analysis_unit_count, truncated, artifact_count, output_digest,
                created_at
            ) VALUES (
                :analysis_run_id, 'amazon', 'zh-CN', '{}', '[]',
                'sha256:input', '{}', 'analysis_snapshot_v1', 'test',
                0, 0, 0, 0, 'sha256:output', :created_at
            )
            """
        ),
        {"analysis_run_id": analysis_run_id, "created_at": created_at},
    )

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DatabaseError

from plugin_hub_api.migrations import MigrationRollbackBlocked, apply_pending_migrations


def test_snapshot_endpoint_requires_explicit_migration(client: TestClient) -> None:
    response = client.post(
        "/api/insights/snapshots",
        json={"platform": "amazon", "language": "zh-CN"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "analysis_snapshot_schema_not_ready"


def test_snapshot_creation_is_append_only_idempotent_and_queryable(client: TestClient) -> None:
    apply_pending_migrations(client.app.state.engine)
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
                    "raw_payload": {
                        "review_id": "snapshot-review-1",
                        "rating": 2,
                        "title": "Breaks too quickly",
                        "body": "The product broke after two weeks.",
                        "asin": "B000000001",
                        "captured_at": "2026-07-10T00:00:00+00:00",
                    },
                    "raw_payload_hash": "sha256:test-snapshot-review-1",
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

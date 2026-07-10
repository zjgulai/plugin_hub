from __future__ import annotations

from fastapi.testclient import TestClient


def test_data_asset_summary_reports_durable_counts_without_payloads(client: TestClient) -> None:
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
                    "raw_payload": {
                        "review_id": "R123",
                        "body": "Durable evidence.",
                        "captured_at": "2026-06-05T00:00:00+00:00",
                    },
                    "raw_payload_hash": "sha256:amazon-r123",
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

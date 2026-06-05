from __future__ import annotations

from fastapi.testclient import TestClient


def test_post_collection_run_with_amazon_item_returns_counts(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(platform="amazon"),
            "raw_items": [
                {
                    "platform": "amazon",
                    "source_kind": "amazon_review",
                    "source_object_id": "R123",
                    "raw_schema_version": "amazon-review-v1",
                    "parser_version": "parser-v1",
                    "raw_payload": {
                        "review_id": "R123",
                        "rating": 2,
                        "title": "Useful but breaks fast",
                        "body": "The product worked for two weeks.",
                        "asin": "B000000001",
                        "captured_at": "2026-06-05T00:00:00+00:00",
                    },
                    "raw_payload_hash": "sha256:amazon-r123",
                    "captured_at": "2026-06-05T00:00:00+00:00",
                }
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["collection_run_id"].startswith("run_")
    assert body["raw_item_count"] == 1
    assert body["voc_unit_count"] == 1


def test_post_reddit_thread_then_get_voc_units_by_platform(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
            ),
            "raw_items": [_reddit_thread_item()],
        },
    )

    assert response.status_code == 201

    voc_response = client.get("/api/voc-units", params={"platform": "reddit"})

    assert voc_response.status_code == 200
    items = voc_response.json()["items"]
    assert len(items) == 1
    assert items[0]["thread_id"] == "t3_thread123"


def test_invalid_collection_run_url_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(source_url="not-a-url"),
            "raw_items": [_amazon_review_item()],
        },
    )

    assert response.status_code == 422


def test_string_coverage_confidence_returns_422(client: TestClient) -> None:
    run = _collection_run()
    run["coverage_confidence"] = "0.8"

    response = client.post(
        "/api/collection-runs",
        json={"run": run, "raw_items": [_amazon_review_item()]},
    )

    assert response.status_code == 422


def test_unsupported_source_kind_is_rejected_by_schema(client: TestClient) -> None:
    raw_item = _amazon_review_item()
    raw_item["source_kind"] = "amazon_question"

    response = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(), "raw_items": [raw_item]},
    )

    assert response.status_code == 422


def test_reddit_comment_maps_thread_parent_and_reply_role(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/comment456/",
            ),
            "raw_items": [
                {
                    "platform": "reddit",
                    "source_kind": "reddit_comment",
                    "source_object_id": "t1_comment456",
                    "raw_schema_version": "reddit-comment-v1",
                    "parser_version": "parser-v1",
                    "raw_payload": {
                        "name": "t1_comment456",
                        "body": "The motor noise is the real issue.",
                        "parent_id": "t1_parent999",
                        "link_id": "t3_thread123",
                        "depth": 2,
                        "created_utc": 1780602800.0,
                    },
                    "raw_payload_hash": "sha256:reddit-comment456",
                    "captured_at": "2026-06-05T00:00:00+00:00",
                }
            ],
        },
    )

    assert response.status_code == 201

    voc_response = client.get("/api/voc-units", params={"platform": "reddit"})
    item = voc_response.json()["items"][0]

    assert item["thread_id"] == "t3_thread123"
    assert item["parent_id"] == "t1_parent999"
    assert item["reply_role"] == "nested_reply"


def test_get_voc_units_serializes_url_and_platform_extension(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(), "raw_items": [_amazon_review_item()]},
    )

    assert response.status_code == 201

    voc_response = client.get("/api/voc-units")
    item = voc_response.json()["items"][0]

    assert item["source_url"] == "https://www.amazon.com/product-reviews/B000000001"
    assert isinstance(item["platform_extension"], dict)
    assert item["platform_extension"]["rating"] == 2


def _collection_run(
    *,
    platform: str = "amazon",
    source_url: str = "https://www.amazon.com/product-reviews/B000000001",
) -> dict[str, object]:
    return {
        "platform": platform,
        "source_url": source_url,
        "capture_method": "browser_extension",
        "coverage_scope": {"page": 1, "sort": "recent"},
        "stop_reason": "manual_stop",
        "coverage_confidence": 0.8,
    }


def _amazon_review_item() -> dict[str, object]:
    return {
        "platform": "amazon",
        "source_kind": "amazon_review",
        "source_object_id": "R123",
        "raw_schema_version": "amazon-review-v1",
        "parser_version": "parser-v1",
        "raw_payload": {
            "review_id": "R123",
            "rating": 2,
            "body": "The product worked for two weeks.",
            "captured_at": "2026-06-05T00:00:00+00:00",
        },
        "raw_payload_hash": "sha256:amazon-r123",
        "captured_at": "2026-06-05T00:00:00+00:00",
    }


def _reddit_thread_item() -> dict[str, object]:
    return {
        "platform": "reddit",
        "source_kind": "reddit_thread",
        "source_object_id": "t3_thread123",
        "raw_schema_version": "reddit-thread-v1",
        "parser_version": "parser-v1",
        "raw_payload": {
            "name": "t3_thread123",
            "id": "thread123",
            "title": "Best grinder for espresso?",
            "selftext": "I want a quieter grinder under $300.",
            "author": "buyer_researcher",
            "created_utc": 1780602718.0,
            "score": 42,
        },
        "raw_payload_hash": "sha256:reddit-thread123",
        "captured_at": "2026-06-05T00:00:00+00:00",
    }

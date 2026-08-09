from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import cast
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from plugin_hub_api.payload_hashes import fnv1a64_payload_hash
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.schemas import CanonicalVocUnit, CollectionRun, JsonValue, RawSourceItem


def test_post_collection_run_with_amazon_item_returns_counts(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(platform="amazon"),
            "raw_items": [_amazon_review_item()],
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


def test_voc_pagination_excludes_rows_committed_after_snapshot_boundary(
    client: TestClient,
) -> None:
    for review_id in ("R1", "R2"):
        item = _amazon_review_item()
        item["source_object_id"] = review_id
        cast(dict[str, object], item["raw_payload"])["review_id"] = review_id
        _refresh_payload_hash(item)
        response = client.post(
            "/api/collection-runs",
            json={"run": _collection_run(), "raw_items": [item]},
        )
        assert response.status_code == 201

    first_page = client.get("/api/voc-units", params={"limit": 1, "offset": 0})
    first_body = first_page.json()
    assert first_page.status_code == 200
    assert first_body["total"] == 2
    assert first_body["snapshot_max_id"] is not None

    newest = _amazon_review_item()
    newest["source_object_id"] = "R3"
    cast(dict[str, object], newest["raw_payload"])["review_id"] = "R3"
    _refresh_payload_hash(newest)
    inserted = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(), "raw_items": [newest]},
    )
    assert inserted.status_code == 201

    second_page = client.get(
        "/api/voc-units",
        params={
            "limit": 1,
            "offset": 1,
            "snapshot_max_id": first_body["snapshot_max_id"],
        },
    )
    second_body = second_page.json()

    assert second_page.status_code == 200
    assert second_body["total"] == 2
    assert second_body["snapshot_max_id"] == first_body["snapshot_max_id"]
    assert second_body["items"][0]["source_object_id"] == "R1"


def test_empty_voc_page_returns_zero_snapshot_boundary(client: TestClient) -> None:
    response = client.get("/api/voc-units")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 100,
        "offset": 0,
        "snapshot_max_id": 0,
    }


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


def test_empty_raw_items_are_rejected_by_schema(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(), "raw_items": []},
    )

    assert response.status_code == 422


def test_collection_run_rejects_raw_items_from_another_platform(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(platform="amazon"), "raw_items": [_reddit_thread_item()]},
    )

    assert response.status_code == 422


def test_collection_run_rejects_source_kind_platform_mismatch(client: TestClient) -> None:
    raw_item = _reddit_thread_item()
    raw_item["platform"] = "amazon"

    response = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(platform="amazon"), "raw_items": [raw_item]},
    )

    assert response.status_code == 422


def test_collection_run_rejects_duplicate_source_objects(client: TestClient) -> None:
    raw_item = _amazon_review_item()
    response = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(), "raw_items": [raw_item, raw_item]},
    )

    assert response.status_code == 422


def test_extension_collection_run_rejects_tampered_payload_hash(client: TestClient) -> None:
    run = _collection_run()
    run["capture_method"] = "extension_dom_next_link_walk"
    raw_item = _amazon_review_item()
    raw_item["raw_payload_hash"] = "fnv1a64:0000000000000000"

    response = client.post(
        "/api/collection-runs",
        json={"run": run, "raw_items": [raw_item]},
    )

    assert response.status_code == 422


def test_capture_method_cannot_bypass_direct_upload_hash_verification(
    client: TestClient,
) -> None:
    run = _collection_run()
    run["capture_method"] = "manual_import"
    raw_item = _amazon_review_item()
    raw_item["raw_payload_hash"] = "sha256:caller-controlled"

    response = client.post(
        "/api/collection-runs",
        json={"run": run, "raw_items": [raw_item]},
    )

    assert response.status_code == 422
    assert "raw_payload_hash_mismatch" in response.text


def test_extension_collection_run_accepts_verified_payload_hash(client: TestClient) -> None:
    run = _collection_run()
    run["capture_method"] = "extension_dom_next_link_walk"
    raw_item = _amazon_review_item()
    _refresh_payload_hash(raw_item)

    response = client.post(
        "/api/collection-runs",
        json={"run": run, "raw_items": [raw_item]},
    )

    assert response.status_code == 201


def test_collection_run_rejects_more_than_two_thousand_raw_items(client: TestClient) -> None:
    raw_items: list[dict[str, object]] = []
    for index in range(2001):
        item = _amazon_review_item()
        source_object_id = f"R{index:010d}"
        item["source_object_id"] = source_object_id
        cast(dict[str, object], item["raw_payload"])["review_id"] = source_object_id
        _refresh_payload_hash(item)
        raw_items.append(item)

    response = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(), "raw_items": raw_items},
    )

    assert response.status_code == 422
    assert any(
        error["type"] == "too_long" and error["loc"] == ["body", "raw_items"]
        for error in response.json()["detail"]
    )


def test_reddit_comment_maps_thread_parent_and_reply_role(client: TestClient) -> None:
    raw_item = _reddit_comment_item()
    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/comment456/",
            ),
            "raw_items": [raw_item],
        },
    )

    assert response.status_code == 201

    voc_response = client.get("/api/voc-units", params={"platform": "reddit"})
    item = voc_response.json()["items"][0]

    assert item["thread_id"] == "t3_thread123"
    assert item["parent_id"] == "t1_parent999"
    assert item["reply_role"] == "nested_reply"


def test_instagram_comment_maps_to_voc_units_by_platform(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="instagram",
                source_url="https://www.instagram.com/p/example/",
            ),
            "raw_items": [_instagram_comment_item()],
        },
    )

    assert response.status_code == 201

    voc_response = client.get("/api/voc-units", params={"platform": "instagram"})
    item = voc_response.json()["items"][0]

    assert item["platform"] == "instagram"
    assert item["source_kind"] == "instagram_comment"
    assert item["source_object_id"] == "18000000000000001"
    assert item["author_display"] == "customer_one"
    assert item["commercial_object_type"] == "instagram_media"
    assert item["platform_extension"]["media_id"] == "17900000000000001"


def test_reddit_comment_without_thread_linkage_returns_422(client: TestClient) -> None:
    raw_item = _reddit_comment_item()
    raw_payload = cast(dict[str, object], raw_item["raw_payload"])
    raw_payload.pop("link_id")
    _refresh_payload_hash(raw_item)

    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/comment456/",
            ),
            "raw_items": [raw_item],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "reddit_comment_thread_id_required"


def test_reddit_comment_invalid_link_id_returns_422_without_persistence(
    client: TestClient,
) -> None:
    raw_item = _reddit_comment_item()
    raw_payload = cast(dict[str, object], raw_item["raw_payload"])
    raw_payload["link_id"] = "not-a-thread"
    _refresh_payload_hash(raw_item)

    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/comment456/",
            ),
            "raw_items": [raw_item],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "reddit_comment_thread_id_required"
    assert client.get("/api/voc-units", params={"platform": "reddit"}).json()["items"] == []


def test_reddit_comment_mismatched_thread_ids_returns_422_without_persistence(
    client: TestClient,
) -> None:
    raw_item = _reddit_comment_item()
    raw_payload = cast(dict[str, object], raw_item["raw_payload"])
    raw_payload["link_id"] = "t3_thread123"
    raw_payload["thread_id"] = "t3_other"
    _refresh_payload_hash(raw_item)

    response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/comment456/",
            ),
            "raw_items": [raw_item],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "reddit_comment_thread_id_required"
    assert client.get("/api/voc-units", params={"platform": "reddit"}).json()["items"] == []


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


def test_get_voc_units_is_bounded_and_reports_total(client: TestClient) -> None:
    first_item = _amazon_review_item()
    second_item = deepcopy(first_item)
    second_item["source_object_id"] = "R124"
    second_payload = cast(dict[str, object], second_item["raw_payload"])
    second_payload["review_id"] = "R124"
    _refresh_payload_hash(second_item)

    for item in (first_item, second_item):
        response = client.post(
            "/api/collection-runs",
            json={"run": _collection_run(), "raw_items": [item]},
        )
        assert response.status_code == 201

    response = client.get("/api/voc-units", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["source_object_id"] == "R124"


def test_collection_run_idempotency_replays_without_duplicate_assets(client: TestClient) -> None:
    payload = {"run": _collection_run(), "raw_items": [_amazon_review_item()]}
    headers = {"Idempotency-Key": f"capture-{'a' * 32}"}

    first = client.post("/api/collection-runs", json=payload, headers=headers)
    second = client.post("/api/collection-runs", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["collection_run_id"] == second.json()["collection_run_id"]
    assert first.json()["replayed"] is False
    assert second.json()["replayed"] is True
    summary = client.get("/api/data-assets/summary").json()
    assert summary["collection_run_count"] == 1
    assert summary["raw_item_count"] == 1
    assert summary["canonical_voc_count"] == 1


def test_collection_run_idempotency_replays_non_utc_offset_timestamp(
    client: TestClient,
) -> None:
    item = deepcopy(_amazon_review_item())
    item["captured_at"] = "2026-06-05T08:00:00+08:00"
    payload = {"run": _collection_run(), "raw_items": [item]}
    headers = {"Idempotency-Key": f"capture-{'z' * 32}"}

    first = client.post("/api/collection-runs", json=payload, headers=headers)
    second = client.post("/api/collection-runs", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["collection_run_id"] == second.json()["collection_run_id"]
    assert second.json()["replayed"] is True


def test_collection_run_idempotency_rejects_key_reuse_with_different_payload(
    client: TestClient,
) -> None:
    headers = {"Idempotency-Key": f"capture-{'b' * 32}"}
    first_payload = {"run": _collection_run(), "raw_items": [_amazon_review_item()]}
    changed_item = deepcopy(_amazon_review_item())
    changed_item["source_object_id"] = "R999"
    changed_raw_payload = cast(dict[str, object], changed_item["raw_payload"])
    changed_raw_payload["review_id"] = "R999"
    _refresh_payload_hash(changed_item)

    first = client.post("/api/collection-runs", json=first_payload, headers=headers)
    second = client.post(
        "/api/collection-runs",
        json={"run": _collection_run(), "raw_items": [changed_item]},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "idempotency_key_payload_conflict"


def test_repository_rolls_back_when_commit_fails() -> None:
    session = MagicMock(spec=Session)
    session.commit.side_effect = SQLAlchemyError("commit failed")
    repository = SqlAlchemyRepository(cast(Session, session))

    try:
        repository.save_collection(
            run=_collection_run_model(),
            raw_items=[_raw_item_model()],
            voc_units=[_voc_unit_model()],
        )
    except SQLAlchemyError:
        pass
    else:
        raise AssertionError("Expected SQLAlchemyError")

    session.rollback.assert_called_once_with()


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
    item: dict[str, object] = {
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
        "raw_payload_hash": "",
        "captured_at": "2026-06-05T00:00:00+00:00",
    }
    _refresh_payload_hash(item)
    return item


def _reddit_thread_item() -> dict[str, object]:
    item: dict[str, object] = {
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
        "raw_payload_hash": "",
        "captured_at": "2026-06-05T00:00:00+00:00",
    }
    _refresh_payload_hash(item)
    return item


def _reddit_comment_item() -> dict[str, object]:
    item: dict[str, object] = {
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
        "raw_payload_hash": "",
        "captured_at": "2026-06-05T00:00:00+00:00",
    }
    _refresh_payload_hash(item)
    return item


def _instagram_comment_item() -> dict[str, object]:
    item: dict[str, object] = {
        "platform": "instagram",
        "source_kind": "instagram_comment",
        "source_object_id": "18000000000000001",
        "raw_schema_version": "instagram-comment-v1",
        "parser_version": "parser-v1",
        "raw_payload": {
            "id": "18000000000000001",
            "text": "This pump is quiet enough for night sessions.",
            "username": "customer_one",
            "timestamp": "2026-06-05T08:30:00+0000",
            "media_id": "17900000000000001",
            "like_count": 4,
            "captured_at": "2026-06-05T10:00:00+00:00",
        },
        "raw_payload_hash": "",
        "captured_at": "2026-06-05T10:00:00+00:00",
    }
    _refresh_payload_hash(item)
    return item


def _refresh_payload_hash(item: dict[str, object]) -> None:
    raw_payload = cast(dict[str, JsonValue], item["raw_payload"])
    item["raw_payload_hash"] = fnv1a64_payload_hash(raw_payload)


def _collection_run_model() -> CollectionRun:
    return CollectionRun.model_validate(
        {
            **_collection_run(),
            "collection_run_id": "run_rollback_test",
            "created_at": datetime(2026, 6, 5, tzinfo=UTC),
        }
    )


def _raw_item_model() -> RawSourceItem:
    return RawSourceItem.model_validate(_amazon_review_item())


def _voc_unit_model() -> CanonicalVocUnit:
    return CanonicalVocUnit.model_validate(
        {
            "platform": "amazon",
            "source_kind": "amazon_review",
            "source_object_id": "R123",
            "collection_run_id": "run_rollback_test",
            "source_url": "https://www.amazon.com/product-reviews/B000000001",
            "captured_at": datetime(2026, 6, 5, tzinfo=UTC),
            "body": "The product worked for two weeks.",
            "coverage_confidence": 0.8,
        }
    )

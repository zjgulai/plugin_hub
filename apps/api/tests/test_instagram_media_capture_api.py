import json
from pathlib import Path

from fastapi.testclient import TestClient

INSTAGRAM_FIXTURE = (
    Path(__file__).parents[3] / "tests" / "fixtures" / "instagram-media-comments.json"
)


def test_post_instagram_media_comment_capture_persists_voc_units(
    client: TestClient,
) -> None:
    payload = json.loads(INSTAGRAM_FIXTURE.read_text())

    response = client.post(
        "/api/instagram-media-comment-captures",
        json={
            "source_url": "https://www.instagram.com/p/example/",
            "payload": payload,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["collection_run_id"].startswith("run_")
    assert body["raw_item_count"] == 2
    assert body["voc_unit_count"] == 2
    assert body["comment_count"] == 2
    assert body["stop_reason"] == "paging_next_not_fetched"

    voc_response = client.get("/api/voc-units", params={"platform": "instagram"})
    assert voc_response.status_code == 200
    items = voc_response.json()["items"]
    assert len(items) == 2
    assert {item["source_kind"] for item in items} == {"instagram_comment"}
    assert items[0]["platform_extension"]["media_id"] == "17900000000000001"


def test_post_instagram_media_comment_capture_rejects_empty_fixture(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/instagram-media-comment-captures",
        json={
            "source_url": "https://www.instagram.com/p/example/",
            "payload": {"comments": {"data": []}},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "instagram_capture_no_raw_items"
    assert client.get("/api/voc-units", params={"platform": "instagram"}).json()["items"] == []


def test_post_instagram_media_comment_capture_rejects_non_instagram_source(
    client: TestClient,
) -> None:
    payload = json.loads(INSTAGRAM_FIXTURE.read_text())

    response = client.post(
        "/api/instagram-media-comment-captures",
        json={
            "source_url": "https://example.com/post/1",
            "payload": payload,
        },
    )

    assert response.status_code == 422
    assert "instagram_source_url_not_allowed" in response.text
    assert client.get("/api/voc-units", params={"platform": "instagram"}).json()["items"] == []

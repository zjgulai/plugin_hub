from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

REDDIT_FIXTURE = Path(__file__).parents[3] / "tests" / "fixtures" / "reddit-thread.json"


def test_post_reddit_thread_capture_fetches_json_and_persists_voc_units(
    client: TestClient,
) -> None:
    requested_urls: list[str] = []

    def fixture_fetcher(url: str) -> str:
        requested_urls.append(url)
        return REDDIT_FIXTURE.read_text()

    client.app.state.reddit_json_fetcher = fixture_fetcher

    response = client.post(
        "/api/reddit-thread-captures",
        json={
            "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["collection_run_id"].startswith("run_")
    assert body["raw_item_count"] == 2
    assert body["voc_unit_count"] == 2
    assert body["json_url"] == (
        "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?raw_json=1"
    )
    assert requested_urls == [body["json_url"]]

    voc_response = client.get("/api/voc-units", params={"platform": "reddit"})
    assert voc_response.status_code == 200
    items = voc_response.json()["items"]
    assert len(items) == 2
    assert {item["source_kind"] for item in items} == {"reddit_thread", "reddit_comment"}
    assert {item["collection_run_id"] for item in items} == {body["collection_run_id"]}


def test_post_reddit_thread_capture_maps_network_errors_to_stable_response(
    client: TestClient,
) -> None:
    def raising_fetcher(_url: str) -> str:
        raise OSError("network unreachable")

    client.app.state.reddit_json_fetcher = raising_fetcher

    response = client.post(
        "/api/reddit-thread-captures",
        json={
            "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "reddit_capture_failed"
    assert client.get("/api/voc-units", params={"platform": "reddit"}).json()["items"] == []

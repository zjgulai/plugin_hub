from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.request import Request

from plugin_hub_api.config import Settings
from plugin_hub_api.services.instagram_graph_capture import (
    InstagramGraphCommentsFetcherClient,
    InstagramGraphConfig,
    InstagramGraphFetchResult,
    build_configured_instagram_graph_comments_fetcher,
    build_instagram_graph_media_comments_url,
    capture_instagram_media_comments_graph,
)


def test_build_instagram_graph_media_comments_url_omits_token_when_sanitized() -> None:
    config = InstagramGraphConfig(access_token="secret-token")

    sanitized_url = build_instagram_graph_media_comments_url(
        media_id="17900000000000001",
        config=config,
        include_access_token=False,
    )
    request_url = build_instagram_graph_media_comments_url(
        media_id="17900000000000001",
        config=config,
        include_access_token=True,
    )

    assert sanitized_url.startswith("https://graph.facebook.com/v25.0/17900000000000001/comments?")
    expected_fields = "fields=id%2Ctext%2Cusername%2Ctimestamp%2Clike_count%2Cparent_id%2Chidden"
    assert expected_fields in sanitized_url
    assert "access_token" not in sanitized_url
    assert "access_token=secret-token" in request_url


def test_configured_instagram_graph_fetcher_requires_access_token() -> None:
    assert build_configured_instagram_graph_comments_fetcher(Settings()) is None
    assert callable(
        build_configured_instagram_graph_comments_fetcher(
            Settings(instagram_graph_access_token="secret-token")
        )
    )


def test_capture_instagram_media_comments_graph_maps_comments_to_raw_items() -> None:
    def fake_fetcher(media_id: str) -> InstagramGraphFetchResult:
        assert media_id == "17900000000000001"
        return InstagramGraphFetchResult(
            payload={
                "data": [
                    {
                        "id": "18000000000000001",
                        "text": "This color is perfect.",
                        "username": "buyer_one",
                        "timestamp": "2026-06-05T10:01:00+0000",
                        "like_count": 4,
                    }
                ],
                "paging": {"next": "https://graph.facebook.com/page2"},
            },
            graph_url="https://graph.facebook.com/v25.0/17900000000000001/comments?fields=id",
        )

    capture = capture_instagram_media_comments_graph(
        media_id="17900000000000001",
        source_url="https://www.instagram.com/p/example/",
        captured_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
        fetcher=fake_fetcher,
    )

    assert capture.media_id == "17900000000000001"
    assert capture.capture.comment_count == 1
    assert capture.capture.stop_reason == "paging_next_not_fetched"
    assert capture.capture.coverage_confidence == 0.74
    assert capture.capture.raw_items[0].source_object_id == "18000000000000001"
    assert capture.capture.raw_items[0].raw_payload["media_id"] == "17900000000000001"
    assert capture.graph_url is not None
    assert "access_token" not in capture.graph_url


def test_instagram_graph_fetcher_client_returns_sanitized_result() -> None:
    requested_urls: list[str] = []

    def fake_http_request(request: Request, timeout: float) -> bytes:
        assert timeout == 20.0
        requested_urls.append(request.full_url)
        return json.dumps({"data": []}).encode("utf-8")

    fetcher = InstagramGraphCommentsFetcherClient(
        InstagramGraphConfig(access_token="secret-token"),
        http_request=fake_http_request,
    )

    result = fetcher("17900000000000001")

    assert requested_urls
    assert "access_token=secret-token" in requested_urls[0]
    assert result.graph_url is not None
    assert "access_token" not in result.graph_url
    assert result.payload == {"data": []}


def test_instagram_graph_fetcher_client_supports_per_task_config_overrides() -> None:
    requested_urls: list[str] = []

    def fake_http_request(request: Request, _timeout: float) -> bytes:
        requested_urls.append(request.full_url)
        return json.dumps({"data": []}).encode("utf-8")

    fetcher = InstagramGraphCommentsFetcherClient(
        InstagramGraphConfig(
            access_token="secret-token",
            api_version="v25.0",
            comment_limit=50,
        ),
        http_request=fake_http_request,
    )

    result = fetcher.with_config_overrides(
        api_version="v26.0",
        comment_limit=7,
    )("17900000000000001")

    assert requested_urls
    assert requested_urls[0].startswith(
        "https://graph.facebook.com/v26.0/17900000000000001/comments?"
    )
    assert "limit=7" in requested_urls[0]
    assert "access_token=secret-token" in requested_urls[0]
    assert result.graph_url is not None
    assert "v26.0" in result.graph_url
    assert "limit=7" in result.graph_url
    assert "access_token" not in result.graph_url

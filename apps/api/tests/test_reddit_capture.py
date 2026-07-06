from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request

import pytest

from plugin_hub_api.config import Settings
from plugin_hub_api.schemas import SourceKind
from plugin_hub_api.services.reddit_capture import (
    RedditOAuthConfig,
    RedditOAuthConfigurationError,
    RedditOAuthJsonFetcher,
    build_configured_reddit_json_fetcher,
    build_reddit_json_url,
    build_reddit_oauth_api_url,
    default_reddit_json_fetcher,
    parse_reddit_thread_json_payload,
)

REDDIT_FIXTURE = Path(__file__).parents[3] / "tests" / "fixtures" / "reddit-thread.json"


def test_build_reddit_json_url_adds_raw_json_without_losing_query() -> None:
    assert (
        build_reddit_json_url(
            "https://www.reddit.com/r/Coffee/comments/thread123/example/?sort=confidence#comments"
        )
        == "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?sort=confidence&raw_json=1"
    )


def test_build_reddit_oauth_api_url_moves_reddit_json_path_to_oauth_host() -> None:
    assert (
        build_reddit_oauth_api_url(
            "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?raw_json=1"
        )
        == "https://oauth.reddit.com/r/Coffee/comments/thread123/example/?raw_json=1"
    )


def test_build_configured_reddit_json_fetcher_uses_default_without_credentials() -> None:
    settings = Settings(reddit_client_id=None, reddit_client_secret=None)

    assert build_configured_reddit_json_fetcher(settings) is default_reddit_json_fetcher


def test_build_configured_reddit_json_fetcher_rejects_partial_oauth_credentials() -> None:
    settings = Settings(reddit_client_id="client-id", reddit_client_secret=None)

    with pytest.raises(RedditOAuthConfigurationError):
        build_configured_reddit_json_fetcher(settings)


def test_reddit_oauth_fetcher_gets_token_and_fetches_from_oauth_api() -> None:
    requests: list[Request] = []
    fixture_body = REDDIT_FIXTURE.read_bytes()

    def http_request(request: Request, _timeout: float) -> bytes:
        requests.append(request)
        if request.full_url == "https://www.reddit.com/api/v1/access_token":
            assert request.data == b"grant_type=client_credentials"
            assert request.get_header("Authorization") == "Basic Y2xpZW50LWlkOmNsaWVudC1zZWNyZXQ="
            assert request.get_header("User-agent") == "PluginHubVOC test agent"
            return (
                b'{"access_token":"token-1","token_type":"bearer","expires_in":3600,"scope":"read"}'
            )
        assert (
            request.full_url
            == "https://oauth.reddit.com/r/Coffee/comments/thread123/example/?raw_json=1"
        )
        assert request.get_header("Authorization") == "bearer token-1"
        assert request.get_header("User-agent") == "PluginHubVOC test agent"
        return fixture_body

    fetcher = RedditOAuthJsonFetcher(
        RedditOAuthConfig(
            client_id="client-id",
            client_secret="client-secret",
            user_agent="PluginHubVOC test agent",
        ),
        http_request=http_request,
    )

    first_payload = fetcher(
        "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?raw_json=1"
    )
    second_payload = fetcher(
        "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?raw_json=1"
    )

    assert first_payload == fixture_body.decode("utf-8")
    assert second_payload == fixture_body.decode("utf-8")
    assert [request.full_url for request in requests].count(
        "https://www.reddit.com/api/v1/access_token"
    ) == 1
    assert [request.full_url for request in requests].count(
        "https://oauth.reddit.com/r/Coffee/comments/thread123/example/?raw_json=1"
    ) == 2


def test_parse_reddit_thread_json_payload_returns_thread_and_comment_raw_items() -> None:
    payload = json.loads(REDDIT_FIXTURE.read_text())

    raw_items, more_node_count, stop_reason = parse_reddit_thread_json_payload(
        payload=payload,
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
        captured_at=datetime(2026, 6, 14, tzinfo=UTC),
    )

    assert stop_reason is None
    assert more_node_count == 0
    assert [item.source_kind for item in raw_items] == [
        SourceKind.REDDIT_THREAD,
        SourceKind.REDDIT_COMMENT,
    ]
    assert raw_items[0].source_object_id == "t3_thread123"
    assert raw_items[1].raw_payload["link_id"] == "t3_thread123"
    assert raw_items[1].raw_payload["thread_id"] == "t3_thread123"
    assert raw_items[0].raw_payload_hash.startswith("sha256:")

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import cast
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from plugin_hub_api.config import Settings
from plugin_hub_api.schemas import JsonValue, ensure_json_object
from plugin_hub_api.services.instagram_capture import (
    InstagramMediaCommentsCaptureResult,
    capture_instagram_media_comments_payload,
)

INSTAGRAM_GRAPH_COMMENT_FIELDS = (
    "id",
    "text",
    "username",
    "timestamp",
    "like_count",
    "parent_id",
    "hidden",
)

type InstagramGraphCommentsFetcher = Callable[[str], object]
type InstagramGraphHttpRequest = Callable[[Request, float], bytes]


@dataclass(frozen=True)
class InstagramGraphConfig:
    access_token: str
    api_version: str = "v25.0"
    graph_api_base_url: str = "https://graph.facebook.com"
    comment_limit: int = 50
    request_timeout_seconds: float = 20.0


@dataclass(frozen=True)
class InstagramGraphFetchResult:
    payload: object
    graph_url: str | None


@dataclass(frozen=True)
class InstagramGraphMediaCommentsCaptureResult:
    capture: InstagramMediaCommentsCaptureResult
    media_id: str
    graph_url: str | None


class InstagramGraphConfigurationError(RuntimeError):
    pass


class InstagramGraphAccessError(RuntimeError):
    pass


class InstagramGraphCommentsFetcherClient:
    def __init__(
        self,
        config: InstagramGraphConfig,
        *,
        http_request: InstagramGraphHttpRequest | None = None,
    ) -> None:
        self._config = config
        self._http_request = http_request if http_request is not None else _urlopen_bytes

    def with_config_overrides(
        self,
        *,
        api_version: str,
        comment_limit: int,
    ) -> InstagramGraphCommentsFetcherClient:
        return InstagramGraphCommentsFetcherClient(
            replace(
                self._config,
                api_version=api_version,
                comment_limit=comment_limit,
            ),
            http_request=self._http_request,
        )

    def __call__(self, media_id: str) -> InstagramGraphFetchResult:
        sanitized_url = build_instagram_graph_media_comments_url(
            media_id=media_id,
            config=self._config,
            include_access_token=False,
        )
        request_url = build_instagram_graph_media_comments_url(
            media_id=media_id,
            config=self._config,
            include_access_token=True,
        )
        request = Request(
            request_url,
            headers={
                "Accept": "application/json",
            },
        )
        try:
            body = self._http_request(request, self._config.request_timeout_seconds)
        except HTTPError as error:
            raise InstagramGraphAccessError(f"instagram_graph_http_{error.code}") from error

        return InstagramGraphFetchResult(
            payload=_parse_graph_response_body(body),
            graph_url=sanitized_url,
        )


def capture_instagram_media_comments_graph(
    *,
    media_id: str,
    source_url: str,
    captured_at: datetime,
    fetcher: InstagramGraphCommentsFetcher,
) -> InstagramGraphMediaCommentsCaptureResult:
    fetch_result = _coerce_fetch_result(fetcher(media_id))
    payload = _payload_with_media_context(
        media_id=media_id,
        payload=fetch_result.payload,
    )
    return InstagramGraphMediaCommentsCaptureResult(
        capture=capture_instagram_media_comments_payload(
            payload=payload,
            source_url=source_url,
            captured_at=captured_at,
        ),
        media_id=media_id,
        graph_url=fetch_result.graph_url,
    )


def build_configured_instagram_graph_comments_fetcher(
    settings: Settings,
) -> InstagramGraphCommentsFetcher | None:
    if not settings.instagram_graph_access_token:
        return None
    return InstagramGraphCommentsFetcherClient(
        InstagramGraphConfig(
            access_token=settings.instagram_graph_access_token,
            api_version=settings.instagram_graph_api_version,
            graph_api_base_url=settings.instagram_graph_api_base_url,
            comment_limit=settings.instagram_graph_comment_limit,
        )
    )


def build_instagram_graph_media_comments_url(
    *,
    media_id: str,
    config: InstagramGraphConfig,
    include_access_token: bool,
) -> str:
    normalized_media_id = media_id.strip()
    if not normalized_media_id:
        raise InstagramGraphConfigurationError("instagram_graph_media_id_required")

    parsed_base = urlparse(config.graph_api_base_url)
    api_version = config.api_version.strip().strip("/")
    if not api_version:
        raise InstagramGraphConfigurationError("instagram_graph_api_version_required")

    query: dict[str, str] = {
        "fields": ",".join(INSTAGRAM_GRAPH_COMMENT_FIELDS),
        "limit": str(max(1, config.comment_limit)),
    }
    if include_access_token:
        query["access_token"] = config.access_token

    return urlunparse(
        (
            parsed_base.scheme or "https",
            parsed_base.netloc or "graph.facebook.com",
            f"/{api_version}/{normalized_media_id}/comments",
            "",
            urlencode(query),
            "",
        )
    )


def _coerce_fetch_result(value: object) -> InstagramGraphFetchResult:
    if isinstance(value, InstagramGraphFetchResult):
        return value
    return InstagramGraphFetchResult(payload=value, graph_url=None)


def _payload_with_media_context(
    *,
    media_id: str,
    payload: object,
) -> dict[str, JsonValue]:
    try:
        graph_payload = ensure_json_object(payload)
    except ValueError as error:
        raise InstagramGraphAccessError("instagram_graph_invalid_response") from error

    return ensure_json_object(
        {
            "id": media_id,
            "comments": graph_payload,
        }
    )


def _parse_graph_response_body(body: bytes) -> dict[str, JsonValue]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise InstagramGraphAccessError("instagram_graph_invalid_json") from error

    try:
        graph_payload = ensure_json_object(payload)
    except ValueError as error:
        raise InstagramGraphAccessError("instagram_graph_invalid_response") from error

    graph_error = graph_payload.get("error")
    if isinstance(graph_error, dict):
        raise InstagramGraphAccessError(_graph_error_code(graph_error))

    return graph_payload


def _graph_error_code(graph_error: dict[str, JsonValue]) -> str:
    code = graph_error.get("code")
    if isinstance(code, str) and code:
        return f"instagram_graph_error_{code}"
    if isinstance(code, int):
        return f"instagram_graph_error_{code}"
    return "instagram_graph_error"


def _urlopen_bytes(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return cast(bytes, response.read())

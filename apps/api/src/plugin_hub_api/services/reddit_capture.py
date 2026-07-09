from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from plugin_hub_api.config import Settings
from plugin_hub_api.schemas import (
    JsonValue,
    Platform,
    RawSourceItem,
    SourceKind,
    ensure_json_object,
)

THREAD_RAW_SCHEMA_VERSION = "raw_reddit_thread_v1"
COMMENT_RAW_SCHEMA_VERSION = "raw_reddit_comment_v1"
PARSER_VERSION = "server-reddit-json-parser@0.1.0"
THREAD_FIELD_KEYS = (
    "name",
    "id",
    "title",
    "selftext",
    "author",
    "subreddit",
    "subreddit_name_prefixed",
    "created_utc",
    "score",
    "upvote_ratio",
    "num_comments",
    "locked",
    "archived",
    "stickied",
    "link_flair_text",
    "permalink",
    "url",
)
COMMENT_FIELD_KEYS = (
    "name",
    "id",
    "body",
    "author",
    "parent_id",
    "link_id",
    "thread_id",
    "depth",
    "created_utc",
    "score",
    "is_submitter",
    "controversiality",
    "subreddit",
    "subreddit_name_prefixed",
    "permalink",
    "comment_flair",
    "author_flair_text",
)
MORE_FIELD_KEYS = ("id", "parent_id", "children", "depth")

type RedditJsonFetcher = Callable[[str], object]
type RedditHttpRequest = Callable[[Request, float], bytes]


@dataclass(frozen=True)
class RedditCaptureResult:
    raw_items: list[RawSourceItem]
    json_url: str
    more_node_count: int
    stop_reason: str | None
    coverage_confidence: float


@dataclass(frozen=True)
class RedditOAuthConfig:
    client_id: str
    client_secret: str
    user_agent: str
    token_url: str = "https://www.reddit.com/api/v1/access_token"
    oauth_api_base_url: str = "https://oauth.reddit.com"
    request_timeout_seconds: float = 20.0


@dataclass(frozen=True)
class RedditAccessToken:
    access_token: str
    token_type: str
    expires_at: datetime
    scope: str | None


class RedditOAuthConfigurationError(RuntimeError):
    pass


class RedditOAuthTokenError(RuntimeError):
    pass


class RedditUpstreamAccessError(RuntimeError):
    pass


class RedditOAuthJsonFetcher:
    def __init__(
        self,
        config: RedditOAuthConfig,
        *,
        http_request: RedditHttpRequest | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._http_request = http_request if http_request is not None else _urlopen_bytes
        self._now = now if now is not None else lambda: datetime.now(tz=UTC)
        self._cached_token: RedditAccessToken | None = None

    def __call__(self, url: str) -> str:
        token = self._access_token()
        request = Request(
            build_reddit_oauth_api_url(url, base_url=self._config.oauth_api_base_url),
            headers={
                "Accept": "application/json",
                "Authorization": f"{token.token_type} {token.access_token}",
                "User-Agent": self._config.user_agent,
            },
        )
        try:
            body = self._http_request(request, self._config.request_timeout_seconds)
        except HTTPError as error:
            raise RedditUpstreamAccessError(f"reddit_upstream_http_{error.code}") from error
        return body.decode("utf-8")

    def _access_token(self) -> RedditAccessToken:
        if self._cached_token is not None and self._cached_token.expires_at > (
            self._now() + timedelta(seconds=60)
        ):
            return self._cached_token

        credentials = f"{self._config.client_id}:{self._config.client_secret}".encode()
        request = Request(
            self._config.token_url,
            data=urlencode({"grant_type": "client_credentials"}).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {base64.b64encode(credentials).decode('ascii')}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self._config.user_agent,
            },
            method="POST",
        )
        try:
            body = self._http_request(request, self._config.request_timeout_seconds)
        except HTTPError as error:
            raise RedditOAuthTokenError(f"reddit_oauth_token_http_{error.code}") from error

        token = _parse_oauth_token_response(body, now=self._now())
        self._cached_token = token
        return token


@dataclass(frozen=True)
class _CommentTraversalResult:
    raw_items: list[RawSourceItem]
    more_node_count: int
    depth_limited: bool


def capture_reddit_thread_json(
    *,
    source_url: str,
    captured_at: datetime,
    fetcher: RedditJsonFetcher | None = None,
    max_comment_depth: int | None = None,
) -> RedditCaptureResult:
    json_url = build_reddit_json_url(source_url)
    resolved_fetcher = fetcher if fetcher is not None else default_reddit_json_fetcher
    payload = resolved_fetcher(json_url)
    parsed_payload = _decode_payload(payload)
    raw_items, more_node_count, stop_reason = parse_reddit_thread_json_payload(
        payload=parsed_payload,
        source_url=source_url,
        captured_at=captured_at,
        max_comment_depth=max_comment_depth,
    )

    return RedditCaptureResult(
        raw_items=raw_items,
        json_url=json_url,
        more_node_count=more_node_count,
        stop_reason=stop_reason,
        coverage_confidence=_reddit_coverage_confidence(
            raw_item_count=len(raw_items),
            more_node_count=more_node_count,
            stop_reason=stop_reason,
        ),
    )


def parse_reddit_thread_json_payload(
    *,
    payload: object,
    source_url: str,
    captured_at: datetime,
    max_comment_depth: int | None = None,
) -> tuple[list[RawSourceItem], int, str | None]:
    listings = _parse_listings(payload)
    if listings is None:
        return [], 0, "invalid_payload"

    thread_listing, comments_listing = listings
    thread_node = _find_thread_node(thread_listing["children"])
    if thread_node is None:
        return [], 0, "missing_thread"

    captured_at_iso = captured_at.astimezone(UTC).isoformat()
    thread_raw_item = _build_thread_raw_source_item(
        data=thread_node["data"],
        source_url=source_url,
        captured_at=captured_at_iso,
    )
    thread_fullname = _reddit_thread_fullname(thread_node["data"])
    if thread_fullname is None:
        return [thread_raw_item], 0, None

    comments = _parse_comments(
        children=comments_listing["children"],
        source_url=source_url,
        captured_at=captured_at_iso,
        thread_fullname=thread_fullname,
        max_comment_depth=max_comment_depth,
        current_depth=0,
    )
    stop_reason = "max_comment_depth_reached" if comments.depth_limited else None
    return [thread_raw_item, *comments.raw_items], comments.more_node_count, stop_reason


def build_reddit_json_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    path = parsed.path if parsed.path.endswith(".json") else f"{parsed.path.rstrip('/')}/.json"
    query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_items["raw_json"] = "1"
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,
            "",
            urlencode(query_items),
            "",
        )
    )


def build_reddit_oauth_api_url(
    json_url: str,
    *,
    base_url: str = "https://oauth.reddit.com",
) -> str:
    parsed = urlparse(json_url)
    parsed_base = urlparse(base_url)
    path = parsed.path
    if path.endswith(".json"):
        path = path.removesuffix(".json")
    return urlunparse(
        (
            parsed_base.scheme or "https",
            parsed_base.netloc or "oauth.reddit.com",
            path,
            "",
            parsed.query,
            "",
        )
    )


def build_configured_reddit_json_fetcher(settings: Settings) -> RedditJsonFetcher:
    has_client_id = bool(settings.reddit_client_id)
    has_client_secret = bool(settings.reddit_client_secret)
    if has_client_id != has_client_secret:
        raise RedditOAuthConfigurationError("reddit_oauth_credentials_incomplete")
    if not has_client_id or not has_client_secret:
        return default_reddit_json_fetcher
    return RedditOAuthJsonFetcher(
        RedditOAuthConfig(
            client_id=cast(str, settings.reddit_client_id),
            client_secret=cast(str, settings.reddit_client_secret),
            user_agent=settings.reddit_user_agent,
        )
    )


def default_reddit_json_fetcher(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "PluginHubVOC/0.1 server-side capture",
        },
    )
    try:
        body = _urlopen_bytes(request, 20)
    except HTTPError as error:
        raise RedditUpstreamAccessError(f"reddit_upstream_http_{error.code}") from error
    return body.decode("utf-8")


def _urlopen_bytes(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return cast(bytes, response.read())


def _parse_oauth_token_response(body: bytes, *, now: datetime) -> RedditAccessToken:
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise RedditOAuthTokenError("reddit_oauth_token_invalid_json") from error

    if not isinstance(payload, dict):
        raise RedditOAuthTokenError("reddit_oauth_token_invalid_response")
    access_token = payload.get("access_token")
    token_type = payload.get("token_type")
    expires_in = payload.get("expires_in")
    scope = payload.get("scope")
    if not isinstance(access_token, str) or not access_token:
        raise RedditOAuthTokenError("reddit_oauth_token_missing_access_token")
    if not isinstance(token_type, str) or not token_type:
        token_type = "bearer"
    if not isinstance(expires_in, int | float) or isinstance(expires_in, bool):
        expires_in = 3600
    if not isinstance(scope, str):
        scope = None
    return RedditAccessToken(
        access_token=access_token,
        token_type=token_type,
        expires_at=now + timedelta(seconds=max(0, int(expires_in))),
        scope=scope,
    )


def _decode_payload(payload: object) -> object:
    if isinstance(payload, bytes):
        return json.loads(payload.decode("utf-8"))
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def _parse_listings(
    payload: object,
) -> tuple[dict[str, list[object]], dict[str, list[object]]] | None:
    if not isinstance(payload, list) or len(payload) < 2:
        return None

    thread_listing = _parse_listing(payload[0])
    comments_listing = _parse_listing(payload[1])
    if thread_listing is None or comments_listing is None:
        return None

    return thread_listing, comments_listing


def _parse_listing(value: object) -> dict[str, list[object]] | None:
    if not isinstance(value, dict):
        return None
    data = value.get("data")
    if not isinstance(data, dict):
        return None
    children = data.get("children")
    if not isinstance(children, list):
        return None
    return {"children": children}


def _find_thread_node(children: list[object]) -> dict[str, dict[str, object]] | None:
    for child in children:
        node = _parse_node(child)
        if node is not None and node["kind"] == "t3":
            return node
    return None


def _parse_node(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    data = value.get("data")
    if not isinstance(kind, str) or not isinstance(data, dict):
        return None
    return {"kind": kind, "data": data}


def _parse_comments(
    *,
    children: list[object],
    source_url: str,
    captured_at: str,
    thread_fullname: str,
    max_comment_depth: int | None,
    current_depth: int,
) -> _CommentTraversalResult:
    raw_items: list[RawSourceItem] = []
    more_node_count = 0
    depth_limited = False

    for child in children:
        node = _parse_node(child)
        if node is None:
            continue

        if node["kind"] == "t1":
            node_depth = _comment_depth(node["data"], current_depth)
            if max_comment_depth is not None and node_depth > max_comment_depth:
                depth_limited = True
                continue
            raw_items.append(
                _build_comment_raw_source_item(
                    data=node["data"],
                    source_url=source_url,
                    captured_at=captured_at,
                    thread_fullname=thread_fullname,
                )
            )
            replies = _parse_listing(node["data"].get("replies"))
            if replies is not None:
                if max_comment_depth is not None and node_depth >= max_comment_depth:
                    depth_limited = True
                else:
                    nested = _parse_comments(
                        children=replies["children"],
                        source_url=source_url,
                        captured_at=captured_at,
                        thread_fullname=thread_fullname,
                        max_comment_depth=max_comment_depth,
                        current_depth=node_depth + 1,
                    )
                    raw_items.extend(nested.raw_items)
                    more_node_count += nested.more_node_count
                    depth_limited = depth_limited or nested.depth_limited
            continue

        if node["kind"] == "more":
            node_depth = _comment_depth(node["data"], current_depth)
            if max_comment_depth is not None and node_depth > max_comment_depth:
                depth_limited = True
                continue
            raw_items.append(
                _build_more_raw_source_item(
                    data=node["data"],
                    source_url=source_url,
                    captured_at=captured_at,
                    thread_fullname=thread_fullname,
                )
            )
            more_node_count += 1

    return _CommentTraversalResult(
        raw_items=raw_items,
        more_node_count=more_node_count,
        depth_limited=depth_limited,
    )


def _comment_depth(data: dict[str, object], fallback: int) -> int:
    depth = data.get("depth")
    if isinstance(depth, int) and depth >= 0:
        return depth
    return fallback


def _build_thread_raw_source_item(
    *,
    data: dict[str, object],
    source_url: str,
    captured_at: str,
) -> RawSourceItem:
    selected_payload = _build_selected_payload(data, THREAD_FIELD_KEYS)
    source_object_id = _reddit_thread_source_object_id(data, selected_payload)
    return _build_raw_source_item(
        source_kind=SourceKind.REDDIT_THREAD,
        source_object_id=source_object_id,
        raw_schema_version=THREAD_RAW_SCHEMA_VERSION,
        selected_payload=selected_payload,
        source_url=source_url,
        captured_at=captured_at,
    )


def _build_comment_raw_source_item(
    *,
    data: dict[str, object],
    source_url: str,
    captured_at: str,
    thread_fullname: str,
) -> RawSourceItem:
    selected_payload = _build_selected_payload(data, COMMENT_FIELD_KEYS)
    _ensure_comment_thread_linkage(selected_payload, thread_fullname)
    comment_flair_text = _clean_json_value(data.get("comment_flair_text"))
    if "comment_flair" not in selected_payload and comment_flair_text is not None:
        selected_payload["comment_flair"] = comment_flair_text

    source_object_id = _reddit_comment_source_object_id(data, selected_payload)
    return _build_raw_source_item(
        source_kind=SourceKind.REDDIT_COMMENT,
        source_object_id=source_object_id,
        raw_schema_version=COMMENT_RAW_SCHEMA_VERSION,
        selected_payload=selected_payload,
        source_url=source_url,
        captured_at=captured_at,
    )


def _build_more_raw_source_item(
    *,
    data: dict[str, object],
    source_url: str,
    captured_at: str,
    thread_fullname: str,
) -> RawSourceItem:
    selected_payload: dict[str, JsonValue] = {
        "kind": "more",
        **_build_selected_payload(data, MORE_FIELD_KEYS),
    }
    _ensure_comment_thread_linkage(selected_payload, thread_fullname)
    source_object_id = _reddit_more_source_object_id(data, selected_payload)
    return _build_raw_source_item(
        source_kind=SourceKind.REDDIT_COMMENT,
        source_object_id=source_object_id,
        raw_schema_version=COMMENT_RAW_SCHEMA_VERSION,
        selected_payload=selected_payload,
        source_url=source_url,
        captured_at=captured_at,
    )


def _build_raw_source_item(
    *,
    source_kind: SourceKind,
    source_object_id: str,
    raw_schema_version: str,
    selected_payload: dict[str, JsonValue],
    source_url: str,
    captured_at: str,
) -> RawSourceItem:
    raw_payload = ensure_json_object(
        {
            **selected_payload,
            "platform": Platform.REDDIT.value,
            "source_kind": source_kind.value,
            "source_object_id": source_object_id,
            "raw_schema_version": raw_schema_version,
            "parser_version": PARSER_VERSION,
            "source_url": source_url,
            "captured_at": captured_at,
        }
    )

    return RawSourceItem.model_validate(
        {
            "platform": Platform.REDDIT,
            "source_kind": source_kind,
            "source_object_id": source_object_id,
            "raw_schema_version": raw_schema_version,
            "parser_version": PARSER_VERSION,
            "raw_payload": raw_payload,
            "raw_payload_hash": _stable_hash(raw_payload),
            "captured_at": captured_at,
        }
    )


def _build_selected_payload(
    data: dict[str, object],
    field_keys: tuple[str, ...],
) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {}
    for key in field_keys:
        value = _clean_json_value(data.get(key))
        if value is not None:
            payload[key] = value
    return payload


def _clean_json_value(value: object) -> JsonValue | None:
    try:
        return _clean_json_value_or_raise(value)
    except ValueError:
        return None


def _clean_json_value_or_raise(value: object) -> JsonValue:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if value == float("inf") or value == float("-inf") or value != value:
            raise ValueError("non_finite_float")
        return value
    if isinstance(value, list):
        return [cleaned for item in value if (cleaned := _clean_json_value(item)) is not None]
    if isinstance(value, dict):
        output: dict[str, JsonValue] = {}
        for key, item in value.items():
            if isinstance(key, str) and (cleaned := _clean_json_value(item)) is not None:
                output[key] = cleaned
        return output
    raise ValueError("unsupported_json_value")


def _ensure_comment_thread_linkage(payload: dict[str, JsonValue], thread_fullname: str) -> None:
    payload["link_id"] = thread_fullname
    payload["thread_id"] = thread_fullname


def _reddit_thread_fullname(data: dict[str, object]) -> str | None:
    name = _string_field(data, "name")
    if name is not None and name.startswith("t3_") and len(name) > len("t3_"):
        return name

    thread_id = _string_field(data, "id")
    if thread_id is not None:
        return f"t3_{thread_id}"
    return None


def _reddit_thread_source_object_id(
    data: dict[str, object],
    fallback_payload: dict[str, JsonValue],
) -> str:
    fullname = _reddit_thread_fullname(data)
    if fullname is not None:
        return fullname
    return _stable_missing_id("reddit_missing_thread_id", fallback_payload)


def _reddit_comment_source_object_id(
    data: dict[str, object],
    fallback_payload: dict[str, JsonValue],
) -> str:
    name = _string_field(data, "name")
    if name is not None:
        return name

    comment_id = _string_field(data, "id")
    if comment_id is not None:
        return f"t1_{comment_id}"
    return _stable_missing_id("reddit_missing_comment_id", fallback_payload)


def _reddit_more_source_object_id(
    data: dict[str, object],
    fallback_payload: dict[str, JsonValue],
) -> str:
    more_id = _string_field(data, "id")
    if more_id is not None:
        return f"more_{more_id}"
    return _stable_missing_id("more_missing_id", fallback_payload)


def _string_field(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _stable_missing_id(prefix: str, value: dict[str, JsonValue]) -> str:
    return f"{prefix}_{_stable_digest(value)[:16]}"


def _stable_hash(value: dict[str, JsonValue]) -> str:
    return f"sha256:{_stable_digest(value)}"


def _stable_digest(value: dict[str, JsonValue]) -> str:
    payload_json = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _reddit_coverage_confidence(
    *,
    raw_item_count: int,
    more_node_count: int,
    stop_reason: str | None,
) -> float:
    if raw_item_count == 0:
        return 0.2
    if stop_reason in {"more_nodes_not_expanded", "max_comment_depth_reached"}:
        return 0.78
    if more_node_count > 0:
        return 0.78
    return 0.92

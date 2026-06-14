from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

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


@dataclass(frozen=True)
class RedditCaptureResult:
    raw_items: list[RawSourceItem]
    json_url: str
    more_node_count: int
    stop_reason: str | None
    coverage_confidence: float


@dataclass(frozen=True)
class _CommentTraversalResult:
    raw_items: list[RawSourceItem]
    more_node_count: int


def capture_reddit_thread_json(
    *,
    source_url: str,
    captured_at: datetime,
    fetcher: RedditJsonFetcher | None = None,
) -> RedditCaptureResult:
    json_url = build_reddit_json_url(source_url)
    resolved_fetcher = fetcher if fetcher is not None else default_reddit_json_fetcher
    payload = resolved_fetcher(json_url)
    parsed_payload = _decode_payload(payload)
    raw_items, more_node_count, stop_reason = parse_reddit_thread_json_payload(
        payload=parsed_payload,
        source_url=source_url,
        captured_at=captured_at,
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
    )
    return [thread_raw_item, *comments.raw_items], comments.more_node_count, None


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


def default_reddit_json_fetcher(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "PluginHubVOC/0.1 server-side capture",
        },
    )
    with urlopen(request, timeout=20) as response:
        body = cast(bytes, response.read())
        return body.decode("utf-8")


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
) -> _CommentTraversalResult:
    raw_items: list[RawSourceItem] = []
    more_node_count = 0

    for child in children:
        node = _parse_node(child)
        if node is None:
            continue

        if node["kind"] == "t1":
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
                nested = _parse_comments(
                    children=replies["children"],
                    source_url=source_url,
                    captured_at=captured_at,
                    thread_fullname=thread_fullname,
                )
                raw_items.extend(nested.raw_items)
                more_node_count += nested.more_node_count
            continue

        if node["kind"] == "more":
            raw_items.append(
                _build_more_raw_source_item(
                    data=node["data"],
                    source_url=source_url,
                    captured_at=captured_at,
                    thread_fullname=thread_fullname,
                )
            )
            more_node_count += 1

    return _CommentTraversalResult(raw_items=raw_items, more_node_count=more_node_count)


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
        return [
            cleaned
            for item in value
            if (cleaned := _clean_json_value(item)) is not None
        ]
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
    if stop_reason == "more_nodes_not_expanded" or more_node_count > 0:
        return 0.78
    return 0.92

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from plugin_hub_api.schemas import (
    JsonValue,
    Platform,
    RawSourceItem,
    SourceKind,
    ensure_json_object,
    ensure_json_value,
)

COMMENT_RAW_SCHEMA_VERSION = "raw_instagram_comment_v1"
PARSER_VERSION = "instagram-graph-comments-parser@0.1.0"
COMMENT_FIELD_KEYS = (
    "id",
    "text",
    "username",
    "timestamp",
    "like_count",
    "media_id",
    "parent_id",
    "hidden",
    "permalink",
)


@dataclass(frozen=True)
class InstagramMediaCommentsCaptureResult:
    raw_items: list[RawSourceItem]
    comment_count: int
    stop_reason: str | None
    coverage_confidence: float


def capture_instagram_media_comments_payload(
    *,
    payload: object,
    source_url: str,
    captured_at: datetime,
) -> InstagramMediaCommentsCaptureResult:
    raw_items, comment_count, stop_reason = parse_instagram_media_comments_payload(
        payload=payload,
        source_url=source_url,
        captured_at=captured_at,
    )
    return InstagramMediaCommentsCaptureResult(
        raw_items=raw_items,
        comment_count=comment_count,
        stop_reason=stop_reason,
        coverage_confidence=_instagram_coverage_confidence(
            raw_item_count=len(raw_items),
            stop_reason=stop_reason,
        ),
    )


def parse_instagram_media_comments_payload(
    *,
    payload: object,
    source_url: str,
    captured_at: datetime,
) -> tuple[list[RawSourceItem], int, str | None]:
    parsed_payload = _parse_payload(payload)
    if parsed_payload is None:
        return [], 0, "invalid_payload"

    media_id = _string_or_none(parsed_payload.get("id")) or _string_or_none(
        parsed_payload.get("media_id")
    )
    permalink = _string_or_none(parsed_payload.get("permalink"))
    comments_payload = _comments_payload(parsed_payload)
    comments = _comment_records(comments_payload)
    if comments is None:
        return [], 0, "missing_comments"

    captured_at_iso = captured_at.astimezone(UTC).isoformat()
    raw_items = [
        _build_comment_raw_source_item(
            comment=comment,
            source_url=source_url,
            captured_at=captured_at_iso,
            media_id=media_id,
            permalink=permalink,
        )
        for comment in comments
    ]
    stop_reason = "paging_next_not_fetched" if _has_next_page(comments_payload) else None
    return raw_items, len(comments), stop_reason


def _parse_payload(payload: object) -> dict[str, JsonValue] | None:
    if not isinstance(payload, dict):
        return None

    try:
        return ensure_json_object(payload)
    except ValueError:
        return None


def _comments_payload(payload: dict[str, JsonValue]) -> JsonValue | None:
    comments = payload.get("comments")
    if comments is not None:
        return comments
    if "data" in payload:
        return payload
    return None


def _comment_records(value: JsonValue | None) -> list[dict[str, JsonValue]] | None:
    if not isinstance(value, dict):
        return None

    data = value.get("data")
    if not isinstance(data, list):
        return None

    comments: list[dict[str, JsonValue]] = []
    for item in data:
        if isinstance(item, dict):
            comments.append(item)
    return comments


def _build_comment_raw_source_item(
    *,
    comment: dict[str, JsonValue],
    source_url: str,
    captured_at: str,
    media_id: str | None,
    permalink: str | None,
) -> RawSourceItem:
    selected_payload = _selected_comment_payload(comment)
    if media_id is not None and "media_id" not in selected_payload:
        selected_payload["media_id"] = media_id
    if permalink is not None and "permalink" not in selected_payload:
        selected_payload["permalink"] = permalink

    source_object_id = _comment_source_object_id(selected_payload)
    raw_payload = {
        **selected_payload,
        "platform": Platform.INSTAGRAM.value,
        "source_kind": SourceKind.INSTAGRAM_COMMENT.value,
        "source_object_id": source_object_id,
        "raw_schema_version": COMMENT_RAW_SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "source_url": source_url,
        "captured_at": captured_at,
    }
    checked_payload = ensure_json_object(raw_payload)

    return RawSourceItem.model_validate(
        {
            "platform": Platform.INSTAGRAM,
            "source_kind": SourceKind.INSTAGRAM_COMMENT,
            "source_object_id": source_object_id,
            "raw_schema_version": COMMENT_RAW_SCHEMA_VERSION,
            "parser_version": PARSER_VERSION,
            "raw_payload": checked_payload,
            "raw_payload_hash": _stable_hash(checked_payload),
            "captured_at": captured_at,
        }
    )


def _selected_comment_payload(comment: dict[str, JsonValue]) -> dict[str, JsonValue]:
    selected: dict[str, JsonValue] = {}
    for key in COMMENT_FIELD_KEYS:
        if key in comment:
            selected[key] = ensure_json_value(comment[key])
    return selected


def _comment_source_object_id(payload: dict[str, JsonValue]) -> str:
    comment_id = _string_or_none(payload.get("id"))
    if comment_id is not None:
        return comment_id
    return _stable_missing_id("instagram_missing_comment_id", payload)


def _has_next_page(value: JsonValue | None) -> bool:
    if not isinstance(value, dict):
        return False
    paging = value.get("paging")
    if not isinstance(paging, dict):
        return False
    next_page = paging.get("next")
    return isinstance(next_page, str) and len(next_page) > 0


def _stable_hash(payload: dict[str, JsonValue]) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload_json.encode('utf-8')).hexdigest()}"


def _stable_missing_id(prefix: str, raw_payload: dict[str, JsonValue]) -> str:
    payload_json = json.dumps(raw_payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _string_or_none(value: JsonValue | None) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _instagram_coverage_confidence(*, raw_item_count: int, stop_reason: str | None) -> float:
    if raw_item_count == 0:
        return 0.2
    if stop_reason == "paging_next_not_fetched":
        return 0.74
    return 0.9

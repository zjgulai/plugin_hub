from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime

from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    JsonValue,
    Platform,
    SourceKind,
    ensure_json_value,
)

AMAZON_EXTENSION_KEYS = (
    "rating",
    "verified_purchase",
    "helpful_vote",
    "review_page",
    "review_position",
    "reviewer_profile_url",
    "sort_by",
    "filter_by_star",
    "variant_context",
)

REDDIT_THREAD_EXTENSION_KEYS = (
    ("subreddit", "subreddit"),
    ("subreddit_name_prefixed", "subreddit_name_prefixed"),
    ("link_flair_text", "post_flair"),
    ("score", "score"),
    ("upvote_ratio", "upvote_ratio"),
    ("num_comments", "num_comments"),
    ("locked", "locked"),
    ("archived", "archived"),
    ("stickied", "stickied"),
)

REDDIT_COMMENT_EXTENSION_KEYS = (
    "score",
    "is_submitter",
    "link_id",
    "controversiality",
    "subreddit",
    "subreddit_name_prefixed",
    "permalink",
)


def map_amazon_review_to_voc(
    *,
    collection_run_id: str,
    source_url: str,
    raw_review: dict[str, JsonValue],
    coverage_confidence: float,
) -> CanonicalVocUnit:
    quality_flags: list[str] = []
    source_object_id = _review_source_object_id(raw_review, quality_flags)
    body = _review_body(raw_review, quality_flags)
    captured_at = _captured_at_with_flags(raw_review, quality_flags)

    return CanonicalVocUnit.model_validate(
        {
            "platform": Platform.AMAZON,
            "source_kind": SourceKind.AMAZON_REVIEW,
            "source_object_id": source_object_id,
            "collection_run_id": collection_run_id,
            "source_url": source_url,
            "captured_at": captured_at,
            "created_at": _created_at_with_flags(raw_review, quality_flags),
            "author_display": _string_or_none(raw_review.get("author")),
            "title": _string_or_none(raw_review.get("title")),
            "body": body,
            "media_refs": _media_refs(raw_review.get("media_refs")),
            "commercial_object_type": "amazon_asin",
            "asin": _string_or_none(raw_review.get("asin")),
            "parent_asin": _string_or_none(raw_review.get("parent_asin")),
            "marketplace": _string_or_none(raw_review.get("marketplace")),
            "quality_flags": quality_flags,
            "coverage_confidence": coverage_confidence,
            "platform_extension": _amazon_platform_extension(raw_review),
        }
    )


def map_reddit_thread_to_voc(
    *,
    collection_run_id: str,
    source_url: str,
    raw_thread: dict[str, JsonValue],
    coverage_confidence: float,
) -> CanonicalVocUnit:
    quality_flags: list[str] = []
    source_object_id = _reddit_thread_source_object_id(raw_thread, quality_flags)
    title = _reddit_thread_title(raw_thread, quality_flags)
    body = _reddit_thread_body(raw_thread, quality_flags)

    return CanonicalVocUnit.model_validate(
        {
            "platform": Platform.REDDIT,
            "source_kind": SourceKind.REDDIT_THREAD,
            "source_object_id": source_object_id,
            "collection_run_id": collection_run_id,
            "source_url": source_url,
            "captured_at": datetime.now(tz=UTC),
            "created_at": _created_utc_with_flags(raw_thread, quality_flags),
            "author_display": _string_or_none(raw_thread.get("author")),
            "title": title,
            "body": body,
            "thread_id": source_object_id,
            "reply_role": "thread_root",
            "quality_flags": quality_flags,
            "coverage_confidence": coverage_confidence,
            "platform_extension": _reddit_thread_platform_extension(raw_thread),
        }
    )


def map_reddit_comment_to_voc(
    *,
    collection_run_id: str,
    source_url: str,
    thread_id: str,
    raw_comment: dict[str, JsonValue],
    coverage_confidence: float,
) -> CanonicalVocUnit:
    quality_flags: list[str] = []
    source_object_id = _reddit_comment_source_object_id(raw_comment, quality_flags)
    body = _reddit_comment_body(raw_comment, quality_flags)
    parent_id = _reddit_comment_parent_id(raw_comment, quality_flags)
    depth = _reddit_comment_depth(raw_comment, quality_flags)

    return CanonicalVocUnit.model_validate(
        {
            "platform": Platform.REDDIT,
            "source_kind": SourceKind.REDDIT_COMMENT,
            "source_object_id": source_object_id,
            "collection_run_id": collection_run_id,
            "source_url": source_url,
            "captured_at": datetime.now(tz=UTC),
            "created_at": _created_utc_with_flags(raw_comment, quality_flags),
            "author_display": _string_or_none(raw_comment.get("author")),
            "body": body,
            "thread_id": thread_id,
            "parent_id": parent_id,
            "depth": depth,
            "reply_role": _reddit_comment_reply_role(
                thread_id=thread_id,
                parent_id=parent_id,
                depth=depth,
            ),
            "quality_flags": quality_flags,
            "coverage_confidence": coverage_confidence,
            "platform_extension": _reddit_comment_platform_extension(raw_comment),
        }
    )


def _review_source_object_id(
    raw_review: dict[str, JsonValue],
    quality_flags: list[str],
) -> str:
    review_id = _string_or_none(raw_review.get("review_id"))
    if review_id is not None:
        return review_id

    quality_flags.append("missing_review_id")
    return _stable_missing_id("amazon_missing_id", raw_review)


def _review_body(raw_review: dict[str, JsonValue], quality_flags: list[str]) -> str:
    body = _string_or_none(raw_review.get("body"))
    if body is None:
        body = _string_or_none(raw_review.get("text"))
    if body is not None:
        return body

    quality_flags.append("missing_body")
    return ""


def _stable_missing_id(prefix: str, raw_payload: dict[str, JsonValue]) -> str:
    payload_json = json.dumps(raw_payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _parse_datetime(value: JsonValue) -> datetime | None:
    if not isinstance(value, str):
        return None

    try:
        parsed = _parse_datetime_string(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _captured_at_with_flags(
    raw_review: dict[str, JsonValue],
    quality_flags: list[str],
) -> datetime:
    value = raw_review.get("captured_at")
    if value is None:
        return datetime.now(tz=UTC)

    parsed = _parse_datetime(value)
    if parsed is None:
        quality_flags.append("invalid_captured_at")
        return datetime.now(tz=UTC)

    if isinstance(value, str) and _datetime_string_is_naive(value):
        quality_flags.append("naive_captured_at_assumed_utc")
    return parsed


def _created_at_with_flags(
    raw_review: dict[str, JsonValue],
    quality_flags: list[str],
) -> datetime | None:
    value = raw_review.get("created_at")
    if value is None:
        return None

    parsed = _parse_datetime(value)
    if parsed is None:
        quality_flags.append("invalid_created_at")
    return parsed


def _datetime_string_is_naive(value: str) -> bool:
    try:
        return _parse_datetime_string(value).tzinfo is None
    except ValueError:
        return False


def _parse_datetime_string(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _amazon_platform_extension(
    raw_review: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    extension: dict[str, JsonValue] = {}
    for key in AMAZON_EXTENSION_KEYS:
        if key in raw_review:
            extension[key] = ensure_json_value(raw_review[key])
    return extension


def _reddit_thread_source_object_id(
    raw_thread: dict[str, JsonValue],
    quality_flags: list[str],
) -> str:
    name = _string_or_none(raw_thread.get("name"))
    if name is not None:
        return name

    thread_id = _string_or_none(raw_thread.get("id"))
    if thread_id is not None:
        return f"t3_{thread_id}"

    quality_flags.append("missing_thread_id")
    return _stable_missing_id("reddit_missing_thread_id", raw_thread)


def _reddit_comment_source_object_id(
    raw_comment: dict[str, JsonValue],
    quality_flags: list[str],
) -> str:
    if _reddit_comment_is_more_node(raw_comment):
        more_id = _string_or_none(raw_comment.get("id"))
        if more_id is not None:
            quality_flags.append("reddit_more_node")
            return f"more_{more_id}"

        quality_flags.append("reddit_more_node")
        return _stable_missing_id("more_missing_id", raw_comment)

    name = _string_or_none(raw_comment.get("name"))
    if name is not None:
        return name

    comment_id = _string_or_none(raw_comment.get("id"))
    if comment_id is not None:
        return f"t1_{comment_id}"

    quality_flags.append("missing_comment_id")
    return _stable_missing_id("reddit_missing_comment_id", raw_comment)


def _reddit_thread_title(
    raw_thread: dict[str, JsonValue],
    quality_flags: list[str],
) -> str | None:
    title = _string_or_none(raw_thread.get("title"))
    if title is None:
        quality_flags.append("missing_thread_title")
    return title


def _reddit_thread_body(
    raw_thread: dict[str, JsonValue],
    quality_flags: list[str],
) -> str:
    body = _string_or_none(raw_thread.get("selftext"))
    if body is None:
        quality_flags.append("missing_thread_body")
        return ""
    return body


def _reddit_comment_body(
    raw_comment: dict[str, JsonValue],
    quality_flags: list[str],
) -> str:
    if _reddit_comment_is_more_node(raw_comment):
        return ""

    body = _string_or_none(raw_comment.get("body"))
    if body is None:
        quality_flags.append("missing_comment_body")
        return ""
    if body in {"[deleted]", "[removed]"}:
        quality_flags.append("reddit_deleted_or_removed")
    return body


def _reddit_comment_is_more_node(raw_comment: dict[str, JsonValue]) -> bool:
    return raw_comment.get("kind") == "more"


def _reddit_comment_parent_id(
    raw_comment: dict[str, JsonValue],
    quality_flags: list[str],
) -> str | None:
    parent_id = _string_or_none(raw_comment.get("parent_id"))
    if parent_id is None and not _reddit_comment_is_more_node(raw_comment):
        quality_flags.append("missing_parent_id")
    return parent_id


def _reddit_comment_depth(
    raw_comment: dict[str, JsonValue],
    quality_flags: list[str],
) -> int | None:
    value = raw_comment.get("depth")
    if isinstance(value, bool):
        if not _reddit_comment_is_more_node(raw_comment):
            quality_flags.append("missing_depth")
        return None
    if isinstance(value, int):
        return value
    if not _reddit_comment_is_more_node(raw_comment):
        quality_flags.append("missing_depth")
    return None


def _reddit_comment_reply_role(
    *,
    thread_id: str,
    parent_id: str | None,
    depth: int | None,
) -> str:
    if parent_id == thread_id or depth == 0:
        return "top_level_reply"
    if parent_id is not None and depth is not None:
        return "nested_reply"
    return "unknown_reply_role"


def _created_utc_with_flags(
    raw_payload: dict[str, JsonValue],
    quality_flags: list[str],
) -> datetime | None:
    if "created_utc" not in raw_payload:
        return None

    parsed = _parse_unix_timestamp(raw_payload["created_utc"])
    if parsed is None:
        quality_flags.append("invalid_created_utc")
    return parsed


def _parse_unix_timestamp(value: JsonValue) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    timestamp = float(value)
    if not math.isfinite(timestamp):
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _reddit_thread_platform_extension(
    raw_thread: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    extension: dict[str, JsonValue] = {}
    for raw_key, extension_key in REDDIT_THREAD_EXTENSION_KEYS:
        if raw_key in raw_thread:
            extension[extension_key] = ensure_json_value(raw_thread[raw_key])
    return extension


def _reddit_comment_platform_extension(
    raw_comment: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    extension: dict[str, JsonValue] = {}
    for key in REDDIT_COMMENT_EXTENSION_KEYS:
        if key in raw_comment:
            extension[key] = ensure_json_value(raw_comment[key])
    comment_flair = raw_comment.get("comment_flair")
    if comment_flair is None:
        comment_flair = raw_comment.get("author_flair_text")
    if comment_flair is not None:
        extension["comment_flair"] = ensure_json_value(comment_flair)
    extension["more_node_count"] = _reddit_more_node_count(raw_comment)
    return extension


def _reddit_more_node_count(raw_comment: dict[str, JsonValue]) -> int:
    children = raw_comment.get("children")
    if isinstance(children, list):
        return len(children)
    return 0


def _media_refs(value: JsonValue) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item for item in value if isinstance(item, str)]
    return []


def _string_or_none(value: JsonValue) -> str | None:
    if isinstance(value, str) and value != "":
        return value
    return None

from __future__ import annotations

import hashlib
import json
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
        if isinstance(value, str):
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
    if parsed is None and isinstance(value, str):
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


def _media_refs(value: JsonValue) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item for item in value if isinstance(item, str)]
    return []


def _string_or_none(value: JsonValue) -> str | None:
    if isinstance(value, str) and value != "":
        return value
    return None

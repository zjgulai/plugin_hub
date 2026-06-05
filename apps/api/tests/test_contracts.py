from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    CollectionRunCreate,
    Platform,
    RawSourceItem,
    SourceKind,
)


def test_collection_run_create_preserves_amazon_pagination_context() -> None:
    payload = CollectionRunCreate.model_validate(
        {
            "platform": Platform.AMAZON,
            "source_url": "https://www.amazon.com/product-reviews/B000000001",
            "capture_method": "extension_dom",
            "coverage_scope": {"segment": "critical_1_2_star", "max_pages": 10},
            "stop_reason": "duplicate_page_hash",
            "coverage_confidence": 0.72,
        }
    )

    assert payload.platform == Platform.AMAZON
    assert payload.coverage_scope["segment"] == "critical_1_2_star"
    assert payload.stop_reason == "duplicate_page_hash"


def test_raw_source_item_keeps_platform_schema_version() -> None:
    item = RawSourceItem(
        platform=Platform.REDDIT,
        source_kind=SourceKind.REDDIT_COMMENT,
        source_object_id="t1_comment123",
        raw_schema_version="raw_reddit_comment_v1",
        parser_version="reddit-json-parser@0.1.0",
        raw_payload={"id": "comment123", "parent_id": "t3_thread123"},
        raw_payload_hash="hash123",
        captured_at=datetime(2026, 6, 5, tzinfo=UTC),
    )

    assert item.raw_schema_version == "raw_reddit_comment_v1"
    assert item.raw_payload["parent_id"] == "t3_thread123"


def test_canonical_voc_unit_allows_platform_specific_context() -> None:
    voc = CanonicalVocUnit.model_validate(
        {
            "platform": Platform.AMAZON,
            "source_kind": SourceKind.AMAZON_REVIEW,
            "source_object_id": "R123",
            "collection_run_id": "run_001",
            "source_url": "https://www.amazon.com/review/R123",
            "captured_at": datetime(2026, 6, 5, tzinfo=UTC),
            "title": "Great but noisy",
            "body": "The motor is strong, but it is louder than expected.",
            "quality_flags": [],
            "coverage_confidence": 0.9,
            "platform_extension": {"rating": 4, "verified_purchase": True},
        }
    )

    assert voc.platform_extension["rating"] == 4
    assert voc.body.startswith("The motor")


def test_collection_run_create_rejects_invalid_source_url() -> None:
    with pytest.raises(ValidationError):
        CollectionRunCreate.model_validate(
            {
                "platform": Platform.AMAZON,
                "source_url": "not-a-url",
                "capture_method": "extension_dom",
                "coverage_confidence": 0.72,
            }
        )


@pytest.mark.parametrize("coverage_confidence", ["0.7", True])
def test_collection_run_create_rejects_non_strict_confidence(
    coverage_confidence: object,
) -> None:
    with pytest.raises(ValidationError):
        CollectionRunCreate.model_validate(
            {
                "platform": Platform.AMAZON,
                "source_url": "https://www.amazon.com/product-reviews/B000000001",
                "capture_method": "extension_dom",
                "coverage_confidence": coverage_confidence,
            }
        )


def test_raw_source_item_rejects_non_json_payload_value() -> None:
    with pytest.raises(ValidationError):
        RawSourceItem.model_validate(
            {
                "platform": Platform.REDDIT,
                "source_kind": SourceKind.REDDIT_COMMENT,
                "source_object_id": "t1_comment123",
                "raw_schema_version": "raw_reddit_comment_v1",
                "parser_version": "reddit-json-parser@0.1.0",
                "raw_payload": {"obj": object()},
                "raw_payload_hash": "hash123",
                "captured_at": datetime(2026, 6, 5, tzinfo=UTC),
            }
        )


def test_canonical_voc_unit_serializes_source_url_as_string() -> None:
    voc = CanonicalVocUnit.model_validate(
        {
            "platform": Platform.AMAZON,
            "source_kind": SourceKind.AMAZON_REVIEW,
            "source_object_id": "R123",
            "collection_run_id": "run_001",
            "source_url": "https://www.amazon.com/review/R123",
            "captured_at": datetime(2026, 6, 5, tzinfo=UTC),
            "body": "The motor is strong, but it is louder than expected.",
            "coverage_confidence": 0.9,
        }
    )

    assert voc.model_dump(mode="json")["source_url"] == "https://www.amazon.com/review/R123"


def test_collection_run_create_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CollectionRunCreate.model_validate(
            {
                "platform": Platform.AMAZON,
                "source_url": "https://www.amazon.com/product-reviews/B000000001",
                "capture_method": "extension_dom",
                "coverage_confidence": 0.72,
                "unexpected_field": "typo",
            }
        )


@pytest.mark.parametrize("coverage_confidence", [0.0, 1.0])
def test_collection_run_create_accepts_confidence_boundaries(
    coverage_confidence: float,
) -> None:
    payload = CollectionRunCreate.model_validate(
        {
            "platform": Platform.AMAZON,
            "source_url": "https://www.amazon.com/product-reviews/B000000001",
            "capture_method": "extension_dom",
            "coverage_confidence": coverage_confidence,
        }
    )

    assert payload.coverage_confidence == coverage_confidence


@pytest.mark.parametrize("coverage_confidence", [-0.01, 1.01])
def test_collection_run_create_rejects_confidence_outside_boundaries(
    coverage_confidence: float,
) -> None:
    with pytest.raises(ValidationError):
        CollectionRunCreate.model_validate(
            {
                "platform": Platform.AMAZON,
                "source_url": "https://www.amazon.com/product-reviews/B000000001",
                "capture_method": "extension_dom",
                "coverage_confidence": coverage_confidence,
            }
        )


@pytest.mark.parametrize("coverage_confidence", [True, "0.7"])
def test_canonical_voc_unit_rejects_non_strict_confidence(
    coverage_confidence: object,
) -> None:
    with pytest.raises(ValidationError):
        CanonicalVocUnit.model_validate(
            {
                "platform": Platform.AMAZON,
                "source_kind": SourceKind.AMAZON_REVIEW,
                "source_object_id": "R123",
                "collection_run_id": "run_001",
                "source_url": "https://www.amazon.com/review/R123",
                "captured_at": datetime(2026, 6, 5, tzinfo=UTC),
                "body": "The motor is strong.",
                "coverage_confidence": coverage_confidence,
            }
        )


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"value": (1, 2)},
        {"value": {1, 2}},
        {"value": b"abc"},
        {"value": Decimal("1.2")},
        {"value": float("nan")},
        {"value": float("inf")},
        {1: "not-a-string-key"},
    ],
)
def test_raw_source_item_rejects_non_json_payload_shapes(
    raw_payload: object,
) -> None:
    with pytest.raises(ValidationError):
        RawSourceItem.model_validate(
            {
                "platform": Platform.REDDIT,
                "source_kind": SourceKind.REDDIT_COMMENT,
                "source_object_id": "t1_comment123",
                "raw_schema_version": "raw_reddit_comment_v1",
                "parser_version": "reddit-json-parser@0.1.0",
                "raw_payload": raw_payload,
                "raw_payload_hash": "hash123",
                "captured_at": datetime(2026, 6, 5, tzinfo=UTC),
            }
        )


def test_json_fields_accept_nested_json_values_and_dump_json() -> None:
    item = RawSourceItem.model_validate(
        {
            "platform": Platform.REDDIT,
            "source_kind": SourceKind.REDDIT_COMMENT,
            "source_object_id": "t1_comment123",
            "raw_schema_version": "raw_reddit_comment_v1",
            "parser_version": "reddit-json-parser@0.1.0",
            "raw_payload": {
                "text": "comment",
                "score": 12,
                "ratio": 0.75,
                "is_submitter": False,
                "missing": None,
                "replies": [{"id": "child", "flags": [True, None]}],
            },
            "raw_payload_hash": "hash123",
            "captured_at": datetime(2026, 6, 5, tzinfo=UTC),
        }
    )

    assert item.raw_payload["replies"] == [{"id": "child", "flags": [True, None]}]
    assert item.model_dump_json()

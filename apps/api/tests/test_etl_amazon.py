from datetime import UTC, datetime

from plugin_hub_api.schemas import Platform, SourceKind
from plugin_hub_api.services.etl import map_amazon_review_to_voc


def test_maps_amazon_review_to_canonical_voc_unit() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_001",
        source_url="https://www.amazon.com/product-reviews/B000000001?pageNumber=2",
        raw_review={
            "review_id": "R123",
            "rating": 2,
            "title": "Useful but breaks fast",
            "body": "The product worked for two weeks and then the switch stopped.",
            "asin": "B000000001",
            "parent_asin": "B000PARENT1",
            "marketplace": "US",
            "author": "Amazon Customer",
            "verified_purchase": True,
            "helpful_vote": 8,
            "media_refs": ["https://images.example/review-1.jpg"],
            "review_page": 2,
            "review_position": 3,
            "reviewer_profile_url": "https://www.amazon.com/gp/profile/amzn1.account.TEST",
            "sort_by": "recent",
            "filter_by_star": "critical",
            "captured_at": "2026-06-05T00:00:00+00:00",
            "created_at": "2026-06-04T12:00:00+00:00",
        },
        coverage_confidence=0.82,
    )

    assert voc.platform == Platform.AMAZON
    assert voc.source_kind == SourceKind.AMAZON_REVIEW
    assert voc.source_object_id == "R123"
    assert voc.asin == "B000000001"
    assert voc.parent_asin == "B000PARENT1"
    assert voc.media_refs == ["https://images.example/review-1.jpg"]
    assert voc.commercial_object_type == "amazon_asin"
    assert voc.created_at is not None
    assert voc.created_at.isoformat() == "2026-06-04T12:00:00+00:00"
    assert voc.platform_extension["rating"] == 2
    assert voc.platform_extension["verified_purchase"] is True
    assert voc.platform_extension["helpful_vote"] == 8
    assert voc.platform_extension["review_page"] == 2
    assert voc.platform_extension["review_position"] == 3
    assert (
        voc.platform_extension["reviewer_profile_url"]
        == "https://www.amazon.com/gp/profile/amzn1.account.TEST"
    )
    assert voc.platform_extension["sort_by"] == "recent"
    assert voc.platform_extension["filter_by_star"] == "critical"
    assert voc.quality_flags == []


def test_amazon_review_without_id_gets_quality_flag() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_002",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "rating": 5,
            "body": "Good value.",
            "captured_at": datetime(2026, 6, 5, tzinfo=UTC).isoformat(),
        },
        coverage_confidence=0.45,
    )

    assert voc.source_object_id.startswith("amazon_missing_id_")
    assert "missing_review_id" in voc.quality_flags
    assert voc.coverage_confidence == 0.45


def test_amazon_review_without_body_gets_empty_body_and_quality_flag() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_003",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "review_id": "R124",
            "rating": 4,
            "captured_at": "2026-06-05T00:00:00+00:00",
        },
        coverage_confidence=0.7,
    )

    assert voc.body == ""
    assert "missing_body" in voc.quality_flags


def test_amazon_review_dump_json_serializes_extension_and_source_url() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_004",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "review_id": "R125",
            "text": "Text fallback is supported.",
            "variant_context": {"color": "black", "size": "M", "badges": ["deal"]},
            "captured_at": "2026-06-05T00:00:00+00:00",
        },
        coverage_confidence=1.0,
    )

    dumped = voc.model_dump(mode="json")

    assert dumped["source_url"] == "https://www.amazon.com/product-reviews/B000000001"
    assert dumped["platform_extension"]["variant_context"] == {
        "color": "black",
        "size": "M",
        "badges": ["deal"],
    }
    assert voc.model_dump_json()

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


def test_missing_review_id_stable_hash_ignores_dict_insertion_order() -> None:
    first = map_amazon_review_to_voc(
        collection_run_id="run_amz_005",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "rating": 3,
            "body": "Useful enough.",
            "captured_at": "2026-06-05T00:00:00+00:00",
        },
        coverage_confidence=0.6,
    )
    second = map_amazon_review_to_voc(
        collection_run_id="run_amz_005",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "captured_at": "2026-06-05T00:00:00+00:00",
            "body": "Useful enough.",
            "rating": 3,
        },
        coverage_confidence=0.6,
    )

    assert first.source_object_id == second.source_object_id


def test_invalid_captured_at_gets_quality_flag_and_aware_fallback() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_006",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "review_id": "R126",
            "body": "Time field is invalid.",
            "captured_at": "not-a-datetime",
        },
        coverage_confidence=0.6,
    )

    assert "invalid_captured_at" in voc.quality_flags
    assert voc.captured_at.tzinfo is not None


def test_invalid_created_at_gets_quality_flag_and_none_created_at() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_007",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "review_id": "R127",
            "body": "Created time field is invalid.",
            "captured_at": "2026-06-05T00:00:00+00:00",
            "created_at": "not-a-datetime",
        },
        coverage_confidence=0.6,
    )

    assert "invalid_created_at" in voc.quality_flags
    assert voc.created_at is None


def test_captured_at_accepts_z_suffix_as_aware_utc_datetime() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_008",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "review_id": "R128",
            "body": "Z suffix time.",
            "captured_at": "2026-06-05T00:00:00Z",
        },
        coverage_confidence=0.6,
    )

    assert voc.captured_at.isoformat() == "2026-06-05T00:00:00+00:00"
    assert voc.captured_at.tzinfo is not None


def test_naive_captured_at_assumes_utc_and_gets_quality_flag() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_009",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "review_id": "R129",
            "body": "Naive captured time.",
            "captured_at": "2026-06-05T00:00:00",
        },
        coverage_confidence=0.6,
    )

    assert voc.captured_at.isoformat() == "2026-06-05T00:00:00+00:00"
    assert voc.captured_at.tzinfo is not None
    assert "naive_captured_at_assumed_utc" in voc.quality_flags


def test_mixed_media_refs_are_dropped() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_010",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "review_id": "R130",
            "body": "Mixed media refs.",
            "media_refs": ["https://images.example/review-2.jpg", 1],
            "captured_at": "2026-06-05T00:00:00+00:00",
        },
        coverage_confidence=0.6,
    )

    assert voc.media_refs == []

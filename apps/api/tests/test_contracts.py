from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from plugin_hub_api import schemas as schema_module
from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    CollectionRunCreate,
    EnrichedVocSignal,
    Platform,
    RawSourceItem,
    RelationEdge,
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


def test_collection_run_create_accepts_extension_supported_smile_amazon_host() -> None:
    payload = CollectionRunCreate.model_validate(
        {
            "platform": Platform.AMAZON,
            "source_url": "https://smile.amazon.com/product-reviews/B000000001",
            "capture_method": "extension_dom",
            "coverage_scope": {"segment": "all_reviews", "max_pages": 1},
            "coverage_confidence": 0.9,
        }
    )

    assert str(payload.source_url).startswith("https://smile.amazon.com/")


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


def test_relation_edge_and_enriched_signal_keep_explainable_context() -> None:
    edge = RelationEdge.model_validate(
        {
            "source_platform": Platform.AMAZON,
            "source_kind": SourceKind.AMAZON_REVIEW,
            "source_object_id": "R123",
            "collection_run_id": "run_001",
            "relation_type": "voc_unit_mentions_asin",
            "from_type": "voc_unit",
            "from_id": "R123",
            "to_type": "amazon_asin",
            "to_id": "B000000001",
            "evidence_strength": 0.82,
            "quality_flags": [],
            "metadata": {"marketplace": "US", "review_page": 2},
        }
    )
    signal = EnrichedVocSignal.model_validate(
        {
            "signal_id": "signal_001",
            "platform": Platform.AMAZON,
            "source_kind": SourceKind.AMAZON_REVIEW,
            "source_object_id": "R123",
            "collection_run_id": "run_001",
            "topic": "noise",
            "aspect": "product_noise",
            "pain_point": "Use environment is disrupted by product noise.",
            "severity": "medium",
            "sentiment": "negative",
            "sentiment_confidence": 0.82,
            "strategy_relevance": 0.78,
            "evidence_strength": 0.82,
            "inference_method": "deterministic_keyword_v1",
            "evidence_examples": [{"body": "The motor is loud.", "platform": "amazon"}],
            "relation_edges": [edge],
        }
    )

    assert signal.relation_edges[0].to_id == "B000000001"
    assert signal.evidence_examples[0]["body"] == "The motor is loud."


def test_insight_brief_contract_keeps_advisor_evidence_and_confidence() -> None:
    insight_brief_model = getattr(schema_module, "InsightBrief", None)

    assert insight_brief_model is not None

    brief = insight_brief_model.model_validate(
        {
            "brief_id": "brief_reddit_thread_t3_thread123",
            "template_id": "reddit_community_commerce_v1",
            "template_version": "v1",
            "language": "zh-CN",
            "advisor_profile": "cross_border_ecommerce_ops",
            "scope": {
                "platform": "reddit",
                "source_object_type": "reddit_thread",
                "source_object_id": "t3_thread123",
                "source_url": "https://www.reddit.com/r/shopify/comments/thread123/example/",
                "collection_run_ids": ["run_001"],
                "coverage_scope": "single_thread",
                "coverage_confidence": 0.58,
            },
            "headline": "Reddit 样本显示转化与信任阻力，需要先补强证据再做强结论。",
            "executive_findings": [
                {
                    "finding_id": "finding_001",
                    "title": "转化阻力集中在信任解释",
                    "business_meaning": "用户讨论已经指向购买前疑虑。",
                    "priority": "P1",
                    "confidence_level": "low",
                    "evidence_ref_ids": ["evidence_001"],
                }
            ],
            "business_signals": [
                {
                    "signal_id": "signal_001",
                    "signal_type": "conversion_blocker",
                    "topic": "trust_gap",
                    "aspect": "trust",
                    "customer_language": ["no sales"],
                    "business_impact": "影响 CVR 和售前解释效率。",
                    "severity": "medium",
                    "priority": "P1",
                    "evidence_strength": "low",
                    "confidence_reason": "单 thread 样本且覆盖置信偏低。",
                    "evidence_ref_ids": ["evidence_001"],
                    "quality_flags": ["low_coverage"],
                }
            ],
            "action_plan": [
                {
                    "action_id": "action_001",
                    "action_type": "content",
                    "title": "把信任疑虑转为 FAQ 与内容选题",
                    "recommendation": "先整理用户原话，再更新 FAQ 和社群回复。",
                    "why_now": "当前样本已经出现购买前疑虑。",
                    "expected_metric": "CVR",
                    "owner_role": "content_ops",
                    "priority": "P1",
                    "effort": "low",
                    "evidence_ref_ids": ["evidence_001"],
                }
            ],
            "evidence_refs": [
                {
                    "evidence_ref_id": "evidence_001",
                    "voc_unit_id": "t3_thread123",
                    "platform": "reddit",
                    "source_kind": "reddit_thread",
                    "source_object_id": "t3_thread123",
                    "quote": "I still get visitors but no sales.",
                    "normalized_quote": "有流量但没有转化。",
                    "rating": None,
                    "relation_edge_ids": [],
                    "quality_flags": ["low_coverage"],
                    "source_url": "https://www.reddit.com/r/shopify/comments/thread123/example/",
                }
            ],
            "confidence": {
                "level": "low",
                "reason": "样本量和覆盖置信不足以支持强结论。",
                "evidence_count": 1,
                "source_diversity": "single_source",
                "coverage_notes": ["coverage_confidence=0.58"],
            },
            "data_gaps": [
                {
                    "gap_type": "low_sample",
                    "description": "当前样本不足，需要补充相邻 thread 或评论。",
                    "recommended_collection": "继续采集同 subreddit 的相邻讨论。",
                    "blocks_confidence": True,
                }
            ],
            "generation_method": "deterministic_template_v1",
            "created_at": "2026-07-08T00:00:00+00:00",
        }
    )

    assert brief.language == "zh-CN"
    assert brief.confidence.level == "low"
    assert brief.data_gaps[0].gap_type == "low_sample"


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


def test_relation_edge_rejects_non_json_metadata_value() -> None:
    with pytest.raises(ValidationError):
        RelationEdge.model_validate(
            {
                "source_platform": Platform.AMAZON,
                "source_kind": SourceKind.AMAZON_REVIEW,
                "source_object_id": "R123",
                "collection_run_id": "run_001",
                "relation_type": "voc_unit_mentions_asin",
                "from_type": "voc_unit",
                "from_id": "R123",
                "to_type": "amazon_asin",
                "to_id": "B000000001",
                "evidence_strength": 0.82,
                "metadata": {"bad": object()},
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

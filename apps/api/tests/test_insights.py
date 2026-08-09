from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi.testclient import TestClient

from plugin_hub_api.payload_hashes import fnv1a64_payload_hash
from plugin_hub_api.schemas import CanonicalVocUnit, JsonValue
from plugin_hub_api.services.insights import (
    build_voc_signal_bundle,
    generate_insight_briefs,
    generate_strategy_notes,
)


def test_generate_strategy_notes_groups_loud_and_noise_as_noise() -> None:
    notes = generate_strategy_notes(
        [
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RLOUD",
                body="The grinder is very loud during every morning use.",
                coverage_confidence=0.9,
            ),
            _voc_unit(
                platform="reddit",
                source_kind="reddit_comment",
                source_object_id="t1_noise",
                body="The motor noise makes it hard to use in an apartment.",
                coverage_confidence=0.7,
            ),
        ]
    )

    assert len(notes) == 1
    note = notes[0]
    assert note["strategy_type"] == "voc_template"
    assert note["topic"] == "noise"
    assert note["evidence_count"] == 2
    assert note["recommendation"] == (
        "Prioritize reducing noise complaints in product messaging and fixes."
    )
    assert note["evidence_strength"] == 0.7
    assert note["quality_flags"] == []
    examples = cast(list[dict[str, JsonValue]], note["evidence_examples"])
    assert examples[0]["body"] == "The grinder is very loud during every morning use."
    assert isinstance(examples[0]["signal_id"], str)
    assert str(examples[0]["signal_id"]).startswith("signal_")
    assert examples[0]["aspect"] == "product_noise"
    assert examples[0]["severity"] == "medium"
    assert examples[1]["relation_edge_count"] == 0


def test_generate_strategy_notes_preserves_low_quality_evidence_flags() -> None:
    notes = generate_strategy_notes(
        [
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RBROKEN",
                body="The lid broke after three days.",
                coverage_confidence=0.42,
                quality_flags=["missing_review_id", "invalid_created_at"],
            ),
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RSTOPPED",
                body="It stopped working after one week.",
                coverage_confidence=0.83,
                quality_flags=["missing_review_id"],
            ),
        ]
    )

    note = notes[0]

    assert note["topic"] == "durability"
    assert note["evidence_count"] == 2
    assert note["evidence_strength"] == 0.42
    examples = cast(list[dict[str, JsonValue]], note["evidence_examples"])
    assert examples[0]["body"] == "The lid broke after three days."
    assert examples[0]["source_object_id"] == "RBROKEN"
    assert examples[0]["source_url"] == "https://example.com/source"
    assert examples[0]["platform"] == "amazon"
    assert examples[0]["collection_run_id"] == "run_insights"
    assert isinstance(examples[0]["signal_id"], str)
    assert str(examples[0]["signal_id"]).startswith("signal_")
    assert examples[0]["aspect"] == "product_reliability"
    assert examples[0]["severity"] == "high"
    assert examples[1]["body"] == "It stopped working after one week."
    assert note["quality_flags"] == ["invalid_created_at", "missing_review_id"]


def test_generate_strategy_notes_empty_units_returns_empty_list() -> None:
    assert generate_strategy_notes([]) == []


def test_generate_strategy_notes_sorts_equal_counts_by_topic() -> None:
    notes = generate_strategy_notes(
        [
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RPRICE",
                body="The price is expensive.",
                coverage_confidence=0.8,
            ),
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RNOISE",
                body="The grinder is loud.",
                coverage_confidence=0.8,
            ),
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RDURABILITY",
                body="The handle broke.",
                coverage_confidence=0.8,
            ),
        ]
    )

    assert [note["topic"] for note in notes] == ["durability", "noise", "price"]


def test_build_voc_signal_bundle_creates_relation_edges_and_signals() -> None:
    bundle = build_voc_signal_bundle(
        [
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RVARIANT",
                body="The grinder is louder than expected.",
                coverage_confidence=0.86,
                asin="B000000001",
                parent_asin="B000PARENT1",
                marketplace="US",
                brand="Acme",
                product_title="Acme Burr Grinder",
                platform_extension={"variant_context": {"color": "black", "size": "small"}},
            ),
            _voc_unit(
                platform="reddit",
                source_kind="reddit_comment",
                source_object_id="t1_child",
                body="The motor noise makes it hard to use in an apartment.",
                coverage_confidence=0.74,
                thread_id="t3_thread123",
                parent_id="t1_parent999",
                reply_role="nested_comment",
                platform_extension={
                    "subreddit": "Coffee",
                    "subreddit_name_prefixed": "r/Coffee",
                },
            ),
        ]
    )

    assert [signal.topic for signal in bundle.enriched_voc_signals] == ["noise", "noise"]
    assert bundle.enriched_voc_signals[0].quality_issue is True
    assert bundle.enriched_voc_signals[1].usage_scenario == "apartment_use"
    edge_types = {edge.relation_type for edge in bundle.relation_edges}
    assert edge_types == {
        "amazon_asin_has_parent",
        "reddit_comment_replies_to_parent_comment",
        "reddit_comment_replies_to_thread",
        "voc_unit_has_variant_context",
        "voc_unit_in_subreddit",
        "voc_unit_mentions_asin",
        "voc_unit_mentions_brand",
    }
    amazon_signal = bundle.enriched_voc_signals[0]
    assert len(amazon_signal.relation_edges) == 4
    assert amazon_signal.relation_edges[0].source_object_id == "RVARIANT"


def test_get_strategy_notes_from_collection_runs_by_platform(client: TestClient) -> None:
    amazon_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="amazon",
                source_url="https://www.amazon.com/product-reviews/B000000001",
                coverage_confidence=0.64,
            ),
            "raw_items": [
                _amazon_review_item(
                    source_object_id="RLOUD",
                    body="The fan noise is loud enough to wake everyone.",
                )
            ],
        },
    )
    reddit_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
                coverage_confidence=0.91,
            ),
            "raw_items": [
                _reddit_thread_item(
                    body="The price is too expensive for a simple grinder.",
                )
            ],
        },
    )

    assert amazon_response.status_code == 201
    assert reddit_response.status_code == 201

    response = client.get("/api/insights/strategy-notes", params={"platform": "amazon"})

    assert response.status_code == 200
    notes = response.json()["items"]
    assert len(notes) == 1
    assert notes[0]["topic"] == "noise"
    assert notes[0]["evidence_strength"] == 0.64
    examples = notes[0]["evidence_examples"]
    assert examples[0]["body"] == "The fan noise is loud enough to wake everyone."
    assert examples[0]["source_object_id"] == "RLOUD"
    assert examples[0]["source_url"] == "https://www.amazon.com/product-reviews/B000000001"
    assert examples[0]["platform"] == "amazon"
    assert examples[0]["source_kind"] == "amazon_review"
    assert examples[0]["collection_run_id"].startswith("run_")
    assert examples[0]["signal_id"].startswith("signal_")
    assert examples[0]["aspect"] == "product_noise"

    all_response = client.get("/api/insights/strategy-notes")

    assert all_response.status_code == 200
    all_notes = all_response.json()["items"]
    assert {note["topic"] for note in all_notes} == {"noise", "price"}


def test_get_voc_signals_from_collection_runs_by_platform(client: TestClient) -> None:
    create_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="amazon",
                source_url="https://www.amazon.com/product-reviews/B000000001",
                coverage_confidence=0.64,
            ),
            "raw_items": [
                _amazon_review_item(
                    source_object_id="RLOUD",
                    body="The fan noise is loud enough to wake everyone.",
                    asin="B000000001",
                    parent_asin="B000PARENT1",
                    marketplace="US",
                )
            ],
        },
    )

    assert create_response.status_code == 201

    response = client.get("/api/insights/voc-signals", params={"platform": "amazon"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["enriched_voc_signals"]) == 1
    signal = payload["enriched_voc_signals"][0]
    assert signal["topic"] == "noise"
    assert signal["aspect"] == "product_noise"
    assert signal["evidence_strength"] == 0.64
    assert signal["inference_method"] == "deterministic_keyword_v1"
    relation_types = {edge["relation_type"] for edge in payload["relation_edges"]}
    assert relation_types == {"amazon_asin_has_parent", "voc_unit_mentions_asin"}


def test_get_reddit_insight_briefs_returns_chinese_advisor_brief(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/shopify/comments/thread123/example/",
                coverage_confidence=0.58,
            ),
            "raw_items": [
                _reddit_thread_item(
                    body=(
                        "Shopify traffic is still 100 visitors a day but no sales. "
                        "I am wondering if trust issues or checkout issues are blocking buyers."
                    ),
                ),
                _reddit_comment_item(
                    source_object_id="t1_comment123",
                    body="I would check trust badges, reviews, and the checkout flow first.",
                    parent_id="t3_thread123",
                ),
            ],
        },
    )

    assert create_response.status_code == 201

    response = client.get("/api/insights/briefs", params={"platform": "reddit"})

    assert response.status_code == 200
    briefs = response.json()["items"]
    assert len(briefs) == 1
    brief = briefs[0]
    assert brief["template_id"] == "reddit_community_commerce_v1"
    assert brief["template_version"] == "v1"
    assert brief["language"] == "zh-CN"
    assert brief["advisor_profile"] == "cross_border_ecommerce_ops"
    assert brief["scope"]["platform"] == "reddit"
    assert brief["scope"]["source_object_type"] == "reddit_thread"
    assert brief["scope"]["source_object_id"] == "t3_thread123"
    assert "转化" in brief["headline"]
    assert brief["confidence"]["level"] == "low"
    assert brief["confidence"]["evidence_count"] == 2
    assert brief["data_gaps"][0]["gap_type"] == "low_sample"
    assert brief["business_signals"][0]["signal_type"] == "conversion_blocker"
    assert brief["business_signals"][0]["priority"] == "P1"
    assert brief["action_plan"][0]["action_type"] in {"content", "faq"}
    assert brief["action_plan"][0]["expected_metric"] == "CVR"
    assert brief["evidence_refs"][0]["platform"] == "reddit"
    assert brief["evidence_refs"][0]["quote"]
    assert brief["generation_method"] == "deterministic_template_v1"


def test_get_amazon_insight_briefs_returns_listing_ops_actions(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="amazon",
                source_url="https://www.amazon.com/product-reviews/B000000001",
                coverage_confidence=0.82,
            ),
            "raw_items": [
                _amazon_review_item(
                    source_object_id="RBROKE",
                    body="The lid broke after three days even though the listing says durable.",
                    asin="B000000001",
                    parent_asin="B000PARENT1",
                    marketplace="US",
                ),
                _amazon_review_item(
                    source_object_id="RPRICE",
                    body="The price feels expensive for this quality level.",
                    asin="B000000001",
                    parent_asin="B000PARENT1",
                    marketplace="US",
                ),
            ],
        },
    )

    assert create_response.status_code == 201

    response = client.get("/api/insights/briefs", params={"platform": "amazon"})

    assert response.status_code == 200
    briefs = response.json()["items"]
    assert len(briefs) == 1
    brief = briefs[0]
    assert brief["template_id"] == "amazon_review_listing_ops_v1"
    assert brief["language"] == "zh-CN"
    assert brief["scope"]["platform"] == "amazon"
    assert brief["scope"]["source_object_type"] == "asin"
    assert brief["scope"]["source_object_id"] == "B000000001"
    assert "Amazon" in brief["headline"]
    signal_types = {signal["signal_type"] for signal in brief["business_signals"]}
    assert "product_quality_issue" in signal_types
    assert "conversion_blocker" in signal_types
    action_types = {action["action_type"] for action in brief["action_plan"]}
    assert action_types & {"listing", "product"}
    assert brief["confidence"]["level"] == "medium"
    assert brief["evidence_refs"][0]["rating"] == 2
    assert brief["evidence_refs"][0]["relation_edge_ids"]


def test_get_amazon_insight_briefs_skips_signals_without_exposed_evidence_ref(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="amazon",
                source_url="https://www.amazon.com/product-reviews/B000000001",
                coverage_confidence=0.82,
            ),
            "raw_items": [
                _amazon_review_item(
                    source_object_id=f"RGENERAL{i}",
                    body="The product works well overall and setup was easy.",
                    asin="B000000001",
                    parent_asin="B000PARENT1",
                    marketplace="US",
                )
                for i in range(8)
            ]
            + [
                _amazon_review_item(
                    source_object_id="RLATEBROKE",
                    body="The lid broke after three days even though the listing says durable.",
                    asin="B000000001",
                    parent_asin="B000PARENT1",
                    marketplace="US",
                )
            ],
        },
    )

    assert create_response.status_code == 201

    response = client.get("/api/insights/briefs", params={"platform": "amazon"})

    assert response.status_code == 200
    brief = response.json()["items"][0]
    exposed_ref_ids = {ref["evidence_ref_id"] for ref in brief["evidence_refs"]}
    assert len(brief["evidence_refs"]) == 8
    assert brief["business_signals"]
    for signal in brief["business_signals"]:
        assert set(signal["evidence_ref_ids"]).issubset(exposed_ref_ids)


def test_brief_evidence_mapping_preserves_repeated_source_id_run_lineage() -> None:
    first_body = "First run lid broke after three days."
    second_body = "Second run motor stopped after one week."
    briefs = generate_insight_briefs(
        [
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="REPEATED",
                collection_run_id="run-first",
                body=first_body,
                coverage_confidence=0.9,
                asin="B000000001",
            ),
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="REPEATED",
                collection_run_id="run-second",
                body=second_body,
                coverage_confidence=0.9,
                asin="B000000001",
            ),
        ]
    )

    assert len(briefs) == 1
    brief = briefs[0].model_dump(mode="json")
    evidence_ids_by_quote = {
        ref["quote"]: ref["evidence_ref_id"] for ref in brief["evidence_refs"]
    }
    assert set(evidence_ids_by_quote) == {first_body, second_body}
    assert len(set(evidence_ids_by_quote.values())) == 2
    matched_signals = 0
    for signal in brief["business_signals"]:
        for customer_quote in signal["customer_language"]:
            expected_ref_id = evidence_ids_by_quote.get(customer_quote)
            if expected_ref_id is not None:
                matched_signals += 1
                assert signal["evidence_ref_ids"] == [expected_ref_id]
    # The deterministic brief currently emits one highest-priority signal for
    # this pair. Its quote belongs to the first run, so the former source-only
    # map (which kept the second run's ref) fails this assertion.
    assert matched_signals == 1


def _voc_unit(
    *,
    platform: str,
    source_kind: str,
    source_object_id: str,
    body: str,
    coverage_confidence: float,
    quality_flags: list[str] | None = None,
    asin: str | None = None,
    parent_asin: str | None = None,
    marketplace: str | None = None,
    brand: str | None = None,
    product_title: str | None = None,
    thread_id: str | None = None,
    parent_id: str | None = None,
    reply_role: str | None = None,
    platform_extension: dict[str, JsonValue] | None = None,
    collection_run_id: str = "run_insights",
) -> CanonicalVocUnit:
    payload: dict[str, object] = {
        "platform": platform,
        "source_kind": source_kind,
        "source_object_id": source_object_id,
        "collection_run_id": collection_run_id,
        "source_url": "https://example.com/source",
        "captured_at": "2026-06-05T00:00:00+00:00",
        "body": body,
        "quality_flags": quality_flags or [],
        "coverage_confidence": coverage_confidence,
    }
    optional_fields: dict[str, object | None] = {
        "asin": asin,
        "parent_asin": parent_asin,
        "marketplace": marketplace,
        "brand": brand,
        "product_title": product_title,
        "thread_id": thread_id,
        "parent_id": parent_id,
        "reply_role": reply_role,
        "platform_extension": platform_extension,
    }
    payload.update({key: value for key, value in optional_fields.items() if value is not None})
    return CanonicalVocUnit.model_validate(payload)


def _collection_run(
    *,
    platform: str,
    source_url: str,
    coverage_confidence: float,
) -> dict[str, object]:
    return {
        "platform": platform,
        "source_url": source_url,
        "capture_method": "browser_extension",
        "coverage_scope": {"page": 1},
        "stop_reason": "manual_stop",
        "coverage_confidence": coverage_confidence,
    }


def _amazon_review_item(
    *,
    source_object_id: str,
    body: str,
    asin: str | None = None,
    parent_asin: str | None = None,
    marketplace: str | None = None,
) -> dict[str, object]:
    raw_payload: dict[str, object] = {
        "review_id": source_object_id,
        "rating": 2,
        "body": body,
        "captured_at": "2026-06-05T00:00:00+00:00",
    }
    if asin is not None:
        raw_payload["asin"] = asin
    if parent_asin is not None:
        raw_payload["parent_asin"] = parent_asin
    if marketplace is not None:
        raw_payload["marketplace"] = marketplace
    return {
        "platform": "amazon",
        "source_kind": "amazon_review",
        "source_object_id": source_object_id,
        "raw_schema_version": "amazon-review-v1",
        "parser_version": "parser-v1",
        "raw_payload": raw_payload,
        "raw_payload_hash": fnv1a64_payload_hash(cast(dict[str, JsonValue], raw_payload)),
        "captured_at": datetime(2026, 6, 5, tzinfo=UTC).isoformat(),
    }


def _reddit_thread_item(*, body: str) -> dict[str, object]:
    raw_payload: dict[str, JsonValue] = {
        "name": "t3_thread123",
        "id": "thread123",
        "title": "Best grinder for espresso?",
        "selftext": body,
        "author": "buyer_researcher",
        "created_utc": 1780602718.0,
        "score": 42,
    }
    return {
        "platform": "reddit",
        "source_kind": "reddit_thread",
        "source_object_id": "t3_thread123",
        "raw_schema_version": "reddit-thread-v1",
        "parser_version": "parser-v1",
        "raw_payload": raw_payload,
        "raw_payload_hash": fnv1a64_payload_hash(raw_payload),
        "captured_at": datetime(2026, 6, 5, tzinfo=UTC).isoformat(),
    }


def _reddit_comment_item(
    *,
    source_object_id: str,
    body: str,
    parent_id: str,
) -> dict[str, object]:
    raw_payload: dict[str, JsonValue] = {
        "name": source_object_id,
        "id": source_object_id.removeprefix("t1_"),
        "body": body,
        "author": "operator_peer",
        "created_utc": 1780602818.0,
        "score": 7,
        "link_id": "t3_thread123",
        "parent_id": parent_id,
        "depth": 1,
        "subreddit": "shopify",
        "subreddit_name_prefixed": "r/shopify",
    }
    return {
        "platform": "reddit",
        "source_kind": "reddit_comment",
        "source_object_id": source_object_id,
        "raw_schema_version": "reddit-comment-v1",
        "parser_version": "parser-v1",
        "raw_payload": raw_payload,
        "raw_payload_hash": fnv1a64_payload_hash(raw_payload),
        "captured_at": datetime(2026, 6, 5, tzinfo=UTC).isoformat(),
    }

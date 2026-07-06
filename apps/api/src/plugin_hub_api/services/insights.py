from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256

from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    EnrichedVocSignal,
    JsonValue,
    Platform,
    RelationEdge,
    SourceKind,
    VocSignalBundle,
)

TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("noise", ("noise", "loud")),
    ("durability", ("break", "broke", "broken", "stopped")),
    ("price", ("price", "expensive")),
)

RECOMMENDATIONS: dict[str, str] = {
    "noise": "Prioritize reducing noise complaints in product messaging and fixes.",
    "durability": "Prioritize durability fixes and expectation-setting around failure points.",
    "price": "Review price objections against positioning, bundle value, and competitor options.",
    "general": "Review the evidence cluster for recurring product and messaging actions.",
}

ASPECT_BY_TOPIC: dict[str, str] = {
    "noise": "product_noise",
    "durability": "product_reliability",
    "price": "value_perception",
    "general": "general_feedback",
}

PAIN_POINT_BY_TOPIC: dict[str, str] = {
    "noise": "Use environment is disrupted by product noise.",
    "durability": "Customer trust is reduced by early product failure.",
    "price": "Purchase conversion is blocked by perceived value gaps.",
    "general": "Evidence needs human review before becoming a specific action.",
}

SEVERITY_BY_TOPIC: dict[str, str] = {
    "noise": "medium",
    "durability": "high",
    "price": "medium",
    "general": "low",
}

STRATEGY_RELEVANCE_BY_TOPIC: dict[str, float] = {
    "noise": 0.78,
    "durability": 0.9,
    "price": 0.82,
    "general": 0.5,
}


@dataclass
class TopicEvidence:
    count: int = 0
    examples: list[dict[str, JsonValue]] = field(default_factory=list)
    evidence_strength: float = 1.0
    quality_flags: set[str] = field(default_factory=set)


def build_voc_signal_bundle(units: list[CanonicalVocUnit]) -> VocSignalBundle:
    relation_edges = generate_relation_edges(units)
    edges_by_source: dict[str, list[RelationEdge]] = {}
    for edge in relation_edges:
        edges_by_source.setdefault(edge.source_object_id, []).append(edge)

    return VocSignalBundle(
        relation_edges=relation_edges,
        enriched_voc_signals=[
            _enriched_voc_signal(
                unit=unit,
                relation_edges=edges_by_source.get(unit.source_object_id, []),
            )
            for unit in units
        ],
    )


def generate_relation_edges(units: list[CanonicalVocUnit]) -> list[RelationEdge]:
    edges: list[RelationEdge] = []
    for unit in units:
        edges.extend(_unit_relation_edges(unit))
    return sorted(
        edges,
        key=lambda edge: (
            edge.source_platform.value,
            edge.source_object_id,
            edge.relation_type,
            edge.from_id,
            edge.to_id,
        ),
    )


def generate_strategy_notes(units: list[CanonicalVocUnit]) -> list[dict[str, JsonValue]]:
    return generate_strategy_notes_from_signals(
        build_voc_signal_bundle(units).enriched_voc_signals
    )


def generate_strategy_notes_from_signals(
    signals: list[EnrichedVocSignal],
) -> list[dict[str, JsonValue]]:
    grouped: dict[str, TopicEvidence] = {}
    for signal in signals:
        evidence = grouped.setdefault(
            signal.topic,
            TopicEvidence(evidence_strength=signal.evidence_strength),
        )
        evidence.count += 1
        _append_signal_example(evidence, signal)
        evidence.evidence_strength = min(evidence.evidence_strength, signal.evidence_strength)
        evidence.quality_flags.update(signal.quality_flags)

    return [
        _strategy_note(topic=topic, evidence=evidence)
        for topic, evidence in sorted(
            grouped.items(),
            key=lambda item: (-item[1].count, item[0]),
        )
    ]


def _topic_for_body(body: str) -> str:
    normalized = body.lower()
    for topic, keywords in TOPIC_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return topic
    return "general"


def _enriched_voc_signal(
    *,
    unit: CanonicalVocUnit,
    relation_edges: list[RelationEdge],
) -> EnrichedVocSignal:
    topic = _topic_for_body(unit.body)
    return EnrichedVocSignal.model_validate(
        {
            "signal_id": _signal_id(unit=unit, topic=topic),
            "platform": unit.platform,
            "source_kind": unit.source_kind,
            "source_object_id": unit.source_object_id,
            "collection_run_id": unit.collection_run_id,
            "topic": topic,
            "aspect": ASPECT_BY_TOPIC[topic],
            "pain_point": PAIN_POINT_BY_TOPIC[topic],
            "severity": SEVERITY_BY_TOPIC[topic],
            "sentiment": "negative" if topic != "general" else None,
            "sentiment_confidence": _sentiment_confidence(unit=unit, topic=topic),
            "purchase_intent": "price_objection" if topic == "price" else None,
            "usage_scenario": _usage_scenario(unit.body),
            "feature_request": False,
            "quality_issue": topic in {"noise", "durability"},
            "comparison_target": _comparison_target(unit.body),
            "strategy_relevance": STRATEGY_RELEVANCE_BY_TOPIC[topic],
            "evidence_strength": unit.coverage_confidence,
            "inference_method": "deterministic_keyword_v1",
            "quality_flags": unit.quality_flags,
            "evidence_examples": [_evidence_example(unit)],
            "relation_edges": relation_edges,
        }
    )


def _unit_relation_edges(unit: CanonicalVocUnit) -> list[RelationEdge]:
    edges: list[RelationEdge] = []

    if unit.platform == Platform.AMAZON:
        if unit.asin is not None:
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="voc_unit_mentions_asin",
                    from_type="voc_unit",
                    from_id=unit.source_object_id,
                    to_type="amazon_asin",
                    to_id=unit.asin,
                    metadata={
                        "marketplace": unit.marketplace,
                        "commercial_object_type": unit.commercial_object_type,
                    },
                )
            )
        if unit.asin is not None and unit.parent_asin is not None:
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="amazon_asin_has_parent",
                    from_type="amazon_asin",
                    from_id=unit.asin,
                    to_type="amazon_parent_asin",
                    to_id=unit.parent_asin,
                    metadata={"marketplace": unit.marketplace},
                )
            )
        variant_context = unit.platform_extension.get("variant_context")
        if isinstance(variant_context, dict) and variant_context:
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="voc_unit_has_variant_context",
                    from_type="voc_unit",
                    from_id=unit.source_object_id,
                    to_type="amazon_variant_context",
                    to_id=_stable_json_id(prefix="variant", value=variant_context),
                    metadata={"variant_context": variant_context},
                )
            )

    if unit.platform == Platform.REDDIT:
        subreddit = _extension_string(unit, "subreddit_name_prefixed") or _extension_string(
            unit,
            "subreddit",
        )
        if unit.source_kind == SourceKind.REDDIT_COMMENT and unit.thread_id is not None:
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="reddit_comment_replies_to_thread",
                    from_type="voc_unit",
                    from_id=unit.source_object_id,
                    to_type="reddit_thread",
                    to_id=unit.thread_id,
                    metadata={"reply_role": unit.reply_role},
                )
            )
        if (
            unit.source_kind == SourceKind.REDDIT_COMMENT
            and unit.parent_id is not None
            and unit.parent_id != unit.thread_id
        ):
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="reddit_comment_replies_to_parent_comment",
                    from_type="voc_unit",
                    from_id=unit.source_object_id,
                    to_type="reddit_comment",
                    to_id=unit.parent_id,
                    metadata={"depth": unit.depth},
                )
            )
        if subreddit is not None:
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="voc_unit_in_subreddit",
                    from_type="voc_unit",
                    from_id=unit.source_object_id,
                    to_type="reddit_subreddit",
                    to_id=subreddit,
                    metadata={"thread_id": unit.thread_id},
                )
            )

    if unit.platform == Platform.INSTAGRAM:
        media_id = _extension_string(unit, "media_id")
        if media_id is not None:
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="instagram_comment_on_media",
                    from_type="voc_unit",
                    from_id=unit.source_object_id,
                    to_type="instagram_media",
                    to_id=media_id,
                    metadata={"reply_role": unit.reply_role},
                )
            )
        if unit.parent_id is not None:
            edges.append(
                _relation_edge(
                    unit=unit,
                    relation_type="instagram_comment_replies_to_parent_comment",
                    from_type="voc_unit",
                    from_id=unit.source_object_id,
                    to_type="instagram_comment",
                    to_id=unit.parent_id,
                    metadata={"reply_role": unit.reply_role},
                )
            )

    if unit.brand is not None:
        edges.append(
            _relation_edge(
                unit=unit,
                relation_type="voc_unit_mentions_brand",
                from_type="voc_unit",
                from_id=unit.source_object_id,
                to_type="brand",
                to_id=unit.brand,
                metadata={"product_title": unit.product_title},
            )
        )

    return edges


def _relation_edge(
    *,
    unit: CanonicalVocUnit,
    relation_type: str,
    from_type: str,
    from_id: str,
    to_type: str,
    to_id: str,
    metadata: dict[str, JsonValue] | None = None,
) -> RelationEdge:
    return RelationEdge.model_validate(
        {
            "source_platform": unit.platform,
            "source_kind": unit.source_kind,
            "source_object_id": unit.source_object_id,
            "relation_type": relation_type,
            "from_type": from_type,
            "from_id": from_id,
            "to_type": to_type,
            "to_id": to_id,
            "evidence_strength": unit.coverage_confidence,
            "quality_flags": unit.quality_flags,
            "metadata": metadata or {},
        }
    )


def _append_signal_example(evidence: TopicEvidence, signal: EnrichedVocSignal) -> None:
    if len(evidence.examples) < 3:
        evidence.examples.append(_signal_evidence_example(signal))


def _signal_evidence_example(signal: EnrichedVocSignal) -> dict[str, JsonValue]:
    example = dict(signal.evidence_examples[0]) if signal.evidence_examples else {}
    example.update(
        {
            "signal_id": signal.signal_id,
            "aspect": signal.aspect,
            "pain_point": signal.pain_point,
            "severity": signal.severity,
            "relation_edge_count": len(signal.relation_edges),
        }
    )
    return example


def _evidence_example(unit: CanonicalVocUnit) -> dict[str, JsonValue]:
    return {
        "body": unit.body,
        "source_object_id": unit.source_object_id,
        "source_url": str(unit.model_dump(mode="json")["source_url"]),
        "platform": unit.platform.value,
        "source_kind": unit.source_kind.value,
        "collection_run_id": unit.collection_run_id,
    }


def _strategy_note(*, topic: str, evidence: TopicEvidence) -> dict[str, JsonValue]:
    evidence_examples: list[JsonValue] = [example for example in evidence.examples]
    quality_flags: list[JsonValue] = [flag for flag in sorted(evidence.quality_flags)]
    return {
        "strategy_type": "voc_template",
        "topic": topic,
        "evidence_count": evidence.count,
        "evidence_examples": evidence_examples,
        "recommendation": RECOMMENDATIONS[topic],
        "evidence_strength": float(evidence.evidence_strength),
        "quality_flags": quality_flags,
    }


def _signal_id(*, unit: CanonicalVocUnit, topic: str) -> str:
    source = f"{unit.collection_run_id}:{unit.source_object_id}:{topic}"
    return f"signal_{sha256(source.encode('utf-8')).hexdigest()[:16]}"


def _sentiment_confidence(*, unit: CanonicalVocUnit, topic: str) -> float | None:
    if topic == "general":
        return None
    return float(min(0.85, max(0.55, unit.coverage_confidence)))


def _usage_scenario(body: str) -> str | None:
    normalized = body.lower()
    if "apartment" in normalized:
        return "apartment_use"
    if "morning" in normalized:
        return "morning_routine"
    if "travel" in normalized:
        return "travel_use"
    return None


def _comparison_target(body: str) -> str | None:
    normalized = body.lower()
    if "competitor" in normalized:
        return "competitor"
    if "than expected" in normalized:
        return "customer_expectation"
    return None


def _extension_string(unit: CanonicalVocUnit, key: str) -> str | None:
    value = unit.platform_extension.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _stable_json_id(*, prefix: str, value: dict[str, JsonValue]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{sha256(encoded.encode('utf-8')).hexdigest()[:16]}"

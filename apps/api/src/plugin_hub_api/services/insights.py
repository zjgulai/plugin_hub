from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256

from plugin_hub_api.schemas import (
    ActionRecommendation,
    BriefConfidence,
    BusinessSignal,
    CanonicalVocUnit,
    DataGap,
    EnrichedVocSignal,
    EvidenceReference,
    ExecutiveFinding,
    InsightBrief,
    InsightScope,
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

ADVISOR_PROFILE = "cross_border_ecommerce_ops"
GENERATION_METHOD = "deterministic_template_v1"
INSIGHT_TEMPLATE_VERSION = "v1"

INSIGHT_TEMPLATE_BY_PLATFORM: dict[Platform, str] = {
    Platform.REDDIT: "reddit_community_commerce_v1",
    Platform.AMAZON: "amazon_review_listing_ops_v1",
}


@dataclass
class TopicEvidence:
    count: int = 0
    examples: list[dict[str, JsonValue]] = field(default_factory=list)
    evidence_strength: float = 1.0
    quality_flags: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class BriefGroupKey:
    platform: Platform
    source_object_type: str
    source_object_id: str


@dataclass
class BriefGroup:
    key: BriefGroupKey
    units: list[CanonicalVocUnit] = field(default_factory=list)


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


def generate_insight_briefs(
    units: list[CanonicalVocUnit],
    *,
    language: str = "zh-CN",
    template_id: str | None = None,
    source_object_type: str | None = None,
    source_object_id: str | None = None,
    limit: int = 20,
    created_at: datetime | None = None,
) -> list[InsightBrief]:
    briefs: list[InsightBrief] = []
    brief_created_at = created_at or datetime.now(tz=UTC)
    for group in _brief_groups(units):
        platform_template_id = INSIGHT_TEMPLATE_BY_PLATFORM.get(group.key.platform)
        if platform_template_id is None:
            continue
        if template_id is not None and template_id != platform_template_id:
            continue
        if source_object_type is not None and source_object_type != group.key.source_object_type:
            continue
        if source_object_id is not None and source_object_id != group.key.source_object_id:
            continue
        briefs.append(
            _insight_brief(
                group=group,
                template_id=platform_template_id,
                language=language,
                created_at=brief_created_at,
            )
        )

    return sorted(briefs, key=lambda brief: brief.brief_id)[:limit]


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


def _brief_groups(units: list[CanonicalVocUnit]) -> list[BriefGroup]:
    groups: dict[BriefGroupKey, BriefGroup] = {}
    for unit in units:
        key = _brief_group_key(unit)
        if key is None:
            continue
        group = groups.setdefault(key, BriefGroup(key=key))
        group.units.append(unit)
    return sorted(
        groups.values(),
        key=lambda group: (
            group.key.platform.value,
            group.key.source_object_type,
            group.key.source_object_id,
        ),
    )


def _brief_group_key(unit: CanonicalVocUnit) -> BriefGroupKey | None:
    if unit.platform == Platform.AMAZON:
        if unit.asin is not None:
            return BriefGroupKey(
                platform=unit.platform,
                source_object_type="asin",
                source_object_id=unit.asin,
            )
        return BriefGroupKey(
            platform=unit.platform,
            source_object_type="amazon_review_set",
            source_object_id=unit.source_object_id,
        )
    if unit.platform == Platform.REDDIT:
        if unit.thread_id is not None:
            return BriefGroupKey(
                platform=unit.platform,
                source_object_type="reddit_thread",
                source_object_id=unit.thread_id,
            )
        return BriefGroupKey(
            platform=unit.platform,
            source_object_type="reddit_discussion",
            source_object_id=unit.source_object_id,
        )
    return None


def _insight_brief(
    *,
    group: BriefGroup,
    template_id: str,
    language: str,
    created_at: datetime,
) -> InsightBrief:
    bundle = build_voc_signal_bundle(group.units)
    evidence_refs = _evidence_references(
        units=group.units,
        relation_edges=bundle.relation_edges,
    )
    evidence_ref_ids_by_source = {
        ref.source_object_id: ref.evidence_ref_id for ref in evidence_refs
    }
    business_signals = _business_signals(
        group=group,
        signals=bundle.enriched_voc_signals,
        evidence_ref_ids_by_source=evidence_ref_ids_by_source,
    )
    return InsightBrief.model_validate(
        {
            "brief_id": _brief_id(group.key),
            "template_id": template_id,
            "template_version": INSIGHT_TEMPLATE_VERSION,
            "language": language,
            "advisor_profile": ADVISOR_PROFILE,
            "scope": _insight_scope(group),
            "headline": _headline(group=group, business_signals=business_signals),
            "executive_findings": _executive_findings(business_signals),
            "business_signals": business_signals,
            "action_plan": _action_plan(
                group=group,
                business_signals=business_signals,
            ),
            "evidence_refs": evidence_refs,
            "confidence": _brief_confidence(group),
            "data_gaps": _data_gaps(group),
            "generation_method": GENERATION_METHOD,
            "created_at": created_at,
        }
    )


def _insight_scope(group: BriefGroup) -> InsightScope:
    coverage_confidence = min(unit.coverage_confidence for unit in group.units)
    return InsightScope.model_validate(
        {
            "platform": group.key.platform,
            "source_object_type": group.key.source_object_type,
            "source_object_id": group.key.source_object_id,
            "source_url": str(group.units[0].model_dump(mode="json")["source_url"]),
            "collection_run_ids": sorted({unit.collection_run_id for unit in group.units}),
            "coverage_scope": _coverage_scope(group),
            "coverage_confidence": coverage_confidence,
        }
    )


def _coverage_scope(group: BriefGroup) -> str:
    if group.key.platform == Platform.REDDIT:
        return "single_thread"
    if group.key.platform == Platform.AMAZON:
        return "asin_review_set"
    return "platform_scope"


def _evidence_references(
    *,
    units: list[CanonicalVocUnit],
    relation_edges: list[RelationEdge],
) -> list[EvidenceReference]:
    edges_by_source: dict[str, list[RelationEdge]] = {}
    for edge in relation_edges:
        edges_by_source.setdefault(edge.source_object_id, []).append(edge)

    return [
        EvidenceReference.model_validate(
            {
                "evidence_ref_id": _evidence_ref_id(unit),
                "voc_unit_id": unit.source_object_id,
                "platform": unit.platform,
                "source_kind": unit.source_kind,
                "source_object_id": unit.source_object_id,
                "quote": _quote(unit.body),
                "normalized_quote": _normalized_quote(unit),
                "rating": _rating(unit),
                "relation_edge_ids": [
                    _relation_edge_ref_id(edge)
                    for edge in edges_by_source.get(unit.source_object_id, [])
                ],
                "quality_flags": _quality_flags(unit),
                "source_url": str(unit.model_dump(mode="json")["source_url"]),
            }
        )
        for unit in units[:8]
    ]


def _business_signals(
    *,
    group: BriefGroup,
    signals: list[EnrichedVocSignal],
    evidence_ref_ids_by_source: dict[str, str],
) -> list[BusinessSignal]:
    output: list[BusinessSignal] = []
    for signal in sorted(signals, key=lambda item: (-item.strategy_relevance, item.signal_id)):
        evidence_ref_id = evidence_ref_ids_by_source.get(signal.source_object_id)
        if evidence_ref_id is None:
            continue
        signal_type = _business_signal_type(group.key.platform, signal)
        output.append(
            BusinessSignal.model_validate(
                {
                    "signal_id": signal.signal_id,
                    "signal_type": signal_type,
                    "topic": _business_topic(group.key.platform, signal, signal_type),
                    "aspect": _business_aspect(group.key.platform, signal, signal_type),
                    "customer_language": _customer_language(signal),
                    "business_impact": _business_impact(group.key.platform, signal_type),
                    "severity": signal.severity,
                    "priority": _priority(signal_type),
                    "evidence_strength": _strength_label(signal.evidence_strength),
                    "confidence_reason": _signal_confidence_reason(signal),
                    "evidence_ref_ids": [evidence_ref_id],
                    "quality_flags": sorted(set(signal.quality_flags)),
                }
            )
        )
    return _dedupe_business_signals(output)[:5]


def _dedupe_business_signals(signals: list[BusinessSignal]) -> list[BusinessSignal]:
    seen: set[tuple[str, str]] = set()
    output: list[BusinessSignal] = []
    for signal in signals:
        key = (signal.signal_type, signal.topic)
        if key in seen:
            continue
        seen.add(key)
        output.append(signal)
    return output


def _business_signal_type(platform: Platform, signal: EnrichedVocSignal) -> str:
    body = _signal_body(signal).lower()
    if platform == Platform.REDDIT:
        if any(keyword in body for keyword in ("no sales", "trust", "checkout", "traffic")):
            return "conversion_blocker"
        if signal.topic == "price":
            return "conversion_blocker"
        if signal.topic in {"durability", "noise"}:
            return "product_quality_issue"
        return "customer_language"
    if signal.topic in {"durability", "noise"}:
        return "product_quality_issue"
    if signal.topic == "price":
        return "conversion_blocker"
    return "positive_purchase_driver"


def _business_topic(platform: Platform, signal: EnrichedVocSignal, signal_type: str) -> str:
    if platform == Platform.REDDIT and signal_type == "conversion_blocker":
        return "trust_gap"
    if platform == Platform.AMAZON and signal_type == "product_quality_issue":
        return "negative_driver"
    if platform == Platform.AMAZON and signal_type == "conversion_blocker":
        return "price_objection"
    return signal.topic


def _business_aspect(platform: Platform, signal: EnrichedVocSignal, signal_type: str) -> str:
    if platform == Platform.REDDIT and signal_type == "conversion_blocker":
        return "trust_and_conversion"
    if platform == Platform.AMAZON and signal_type == "product_quality_issue":
        return "product_quality"
    return signal.aspect


def _business_impact(platform: Platform, signal_type: str) -> str:
    if platform == Platform.REDDIT and signal_type == "conversion_blocker":
        return "影响 CVR、售前解释效率和社群内容切入角度。"
    if platform == Platform.AMAZON and signal_type == "product_quality_issue":
        return "影响转化率、差评风险和产品体验承诺。"
    if signal_type == "conversion_blocker":
        return "影响价格接受度、CVR 和 Listing 说服力。"
    if signal_type == "positive_purchase_driver":
        return "可沉淀为 Listing、广告和图片信息层级的卖点素材。"
    return "可作为运营复核和补样方向。"


def _priority(signal_type: str) -> str:
    if signal_type in {"conversion_blocker", "product_quality_issue"}:
        return "P1"
    return "P2"


def _action_plan(
    *,
    group: BriefGroup,
    business_signals: list[BusinessSignal],
) -> list[ActionRecommendation]:
    actions: list[ActionRecommendation] = []
    for signal in business_signals:
        action = _action_for_signal(group.key.platform, signal)
        if action is not None:
            actions.append(action)
    return _dedupe_actions(actions)[:3]


def _action_for_signal(
    platform: Platform,
    signal: BusinessSignal,
) -> ActionRecommendation | None:
    evidence_ref_ids = signal.evidence_ref_ids
    if platform == Platform.REDDIT and signal.signal_type == "conversion_blocker":
        return _action(
            signal=signal,
            action_type="content",
            title="把信任疑虑转成 FAQ 与社群内容选题",
            recommendation=(
                "先整理用户原话，补充评价、支付安全、退换货和结账解释，"
                "再用于 FAQ 与 Reddit 回复角度。"
            ),
            why_now="当前讨论已经指向有流量但转化受阻，适合先处理信任解释而不是盲目加流量。",
            expected_metric="CVR",
            owner_role="content_ops",
            effort="low",
            evidence_ref_ids=evidence_ref_ids,
        )
    if platform == Platform.AMAZON and signal.signal_type == "product_quality_issue":
        return _action(
            signal=signal,
            action_type="product",
            title="复核差评根因并同步 Listing 预期",
            recommendation=(
                "把质量问题拆给产品或供应链复核，"
                "同时在五点、图片和 FAQ 中明确使用边界。"
            ),
            why_now="差评根因会同时影响转化和退货风险，需要先降低预期落差。",
            expected_metric="CVR",
            owner_role="product_ops",
            effort="medium",
            evidence_ref_ids=evidence_ref_ids,
        )
    if platform == Platform.AMAZON and signal.signal_type == "conversion_blocker":
        return _action(
            signal=signal,
            action_type="listing",
            title="强化价格异议处理和价值表达",
            recommendation=(
                "在标题、五点、A+ 或图片中补足材质、套装、耐用性和售后价值，"
                "减少价格疑虑。"
            ),
            why_now="价格异议已经进入评论证据，会削弱 Listing 说服力。",
            expected_metric="CVR",
            owner_role="listing_ops",
            effort="low",
            evidence_ref_ids=evidence_ref_ids,
        )
    return None


def _action(
    *,
    signal: BusinessSignal,
    action_type: str,
    title: str,
    recommendation: str,
    why_now: str,
    expected_metric: str,
    owner_role: str,
    effort: str,
    evidence_ref_ids: list[str],
) -> ActionRecommendation:
    return ActionRecommendation.model_validate(
        {
            "action_id": _stable_id("action", f"{signal.signal_id}:{action_type}"),
            "action_type": action_type,
            "title": title,
            "recommendation": recommendation,
            "why_now": why_now,
            "expected_metric": expected_metric,
            "owner_role": owner_role,
            "priority": signal.priority,
            "effort": effort,
            "evidence_ref_ids": evidence_ref_ids,
        }
    )


def _dedupe_actions(actions: list[ActionRecommendation]) -> list[ActionRecommendation]:
    seen: set[str] = set()
    output: list[ActionRecommendation] = []
    for action in actions:
        if action.action_type in seen:
            continue
        seen.add(action.action_type)
        output.append(action)
    return output


def _executive_findings(signals: list[BusinessSignal]) -> list[ExecutiveFinding]:
    return [
        ExecutiveFinding.model_validate(
            {
                "finding_id": _stable_id("finding", signal.signal_id),
                "title": _finding_title(signal),
                "business_meaning": signal.business_impact,
                "priority": signal.priority,
                "confidence_level": _signal_confidence_level(signal),
                "evidence_ref_ids": signal.evidence_ref_ids,
            }
        )
        for signal in signals[:3]
    ]


def _finding_title(signal: BusinessSignal) -> str:
    if signal.signal_type == "conversion_blocker":
        return "转化阻力需要运营解释"
    if signal.signal_type == "product_quality_issue":
        return "产品体验问题需要优先复核"
    if signal.signal_type == "positive_purchase_driver":
        return "好评卖点可进入 Listing 与广告"
    return "用户语言可沉淀为运营素材"


def _headline(
    *,
    group: BriefGroup,
    business_signals: list[BusinessSignal],
) -> str:
    signal_types = {signal.signal_type for signal in business_signals}
    if group.key.platform == Platform.REDDIT:
        if "conversion_blocker" in signal_types:
            return "Reddit 样本显示转化与信任阻力，优先补强 FAQ、信任证据和社群解释。"
        return "Reddit 样本更适合作为社区语言和内容角度线索，需要继续补样验证。"
    if "product_quality_issue" in signal_types:
        return "Amazon 评论显示产品体验与 Listing 承诺存在经营风险，优先处理差评根因。"
    return "Amazon 评论提供 Listing 和广告素材线索，建议先提炼高频卖点。"


def _brief_confidence(group: BriefGroup) -> BriefConfidence:
    min_coverage = min(unit.coverage_confidence for unit in group.units)
    evidence_count = len(group.units)
    level = _brief_confidence_level(evidence_count=evidence_count, min_coverage=min_coverage)
    return BriefConfidence.model_validate(
        {
            "level": level,
            "reason": _brief_confidence_reason(level),
            "evidence_count": evidence_count,
            "source_diversity": _source_diversity(group),
            "coverage_notes": [f"coverage_confidence={min_coverage:.2f}"],
        }
    )


def _brief_confidence_level(*, evidence_count: int, min_coverage: float) -> str:
    if evidence_count >= 5 and min_coverage >= 0.8:
        return "high"
    if evidence_count >= 2 and min_coverage >= 0.8:
        return "medium"
    if evidence_count >= 1 and min_coverage >= 0.5:
        return "low"
    return "hypothesis"


def _brief_confidence_reason(level: str) -> str:
    if level == "high":
        return "样本量、覆盖置信和证据一致性足以支持运营优先级判断。"
    if level == "medium":
        return "证据足以形成运营建议，但仍建议结合更多样本复核。"
    if level == "low":
        return "样本量或覆盖置信偏低，建议作为待验证运营假设。"
    return "当前证据不足，只能作为补采方向。"


def _source_diversity(group: BriefGroup) -> str:
    if group.key.source_object_type == "reddit_thread":
        return "single_thread"
    if group.key.source_object_type == "asin":
        return "single_asin"
    return "single_source"


def _data_gaps(group: BriefGroup) -> list[DataGap]:
    gaps: list[DataGap] = []
    min_coverage = min(unit.coverage_confidence for unit in group.units)
    if len(group.units) < 3:
        gaps.append(
            DataGap.model_validate(
                {
                    "gap_type": "low_sample",
                    "description": "当前样本量不足，强结论需要更多 VOC 证据支撑。",
                    "recommended_collection": _recommended_collection(group),
                    "blocks_confidence": min_coverage < 0.8,
                }
            )
        )
    if min_coverage < 0.65:
        gaps.append(
            DataGap.model_validate(
                {
                    "gap_type": "low_coverage",
                    "description": "采集覆盖置信偏低，结论应先降级为待验证假设。",
                    "recommended_collection": _recommended_collection(group),
                    "blocks_confidence": True,
                }
            )
        )
    return gaps


def _recommended_collection(group: BriefGroup) -> str:
    if group.key.platform == Platform.REDDIT:
        return "继续采集同 subreddit 的相邻 thread 和更多评论。"
    return "补采 recent、critical 1/2 star、verified 和 media reviews。"


def _signal_confidence_reason(signal: EnrichedVocSignal) -> str:
    if signal.evidence_strength >= 0.8:
        return "证据覆盖置信较高，可进入运营优先级讨论。"
    if signal.evidence_strength >= 0.5:
        return "证据可支持方向判断，但需要补样复核。"
    return "证据强度偏低，只能作为假设。"


def _signal_confidence_level(signal: BusinessSignal) -> str:
    if signal.evidence_strength == "high":
        return "medium"
    if signal.evidence_strength == "medium":
        return "low"
    return "hypothesis"


def _strength_label(value: float) -> str:
    if value >= 0.8:
        return "high"
    if value >= 0.5:
        return "medium"
    return "low"


def _customer_language(signal: EnrichedVocSignal) -> list[str]:
    body = _signal_body(signal)
    return [_quote(body)] if body else []


def _signal_body(signal: EnrichedVocSignal) -> str:
    if signal.evidence_examples:
        body = signal.evidence_examples[0].get("body")
        if isinstance(body, str):
            return body
    return ""


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


def _quote(body: str, *, max_length: int = 240) -> str:
    normalized = " ".join(body.split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3].rstrip()}..."


def _normalized_quote(unit: CanonicalVocUnit) -> str | None:
    body = unit.body.lower()
    if unit.platform == Platform.REDDIT and any(
        keyword in body for keyword in ("no sales", "trust", "checkout")
    ):
        return "用户讨论指向转化或信任阻力。"
    if unit.platform == Platform.AMAZON and any(
        keyword in body for keyword in ("broke", "broken", "stopped")
    ):
        return "评论指向产品质量或耐用性问题。"
    if "price" in body or "expensive" in body:
        return "用户表达了价格或价值感知异议。"
    return None


def _rating(unit: CanonicalVocUnit) -> float | None:
    rating = unit.platform_extension.get("rating")
    if isinstance(rating, int | float) and not isinstance(rating, bool):
        return float(rating)
    return None


def _quality_flags(unit: CanonicalVocUnit) -> list[str]:
    flags = set(unit.quality_flags)
    if unit.coverage_confidence < 0.65:
        flags.add("low_coverage")
    return sorted(flags)


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


def _brief_id(key: BriefGroupKey) -> str:
    source = f"{key.platform.value}:{key.source_object_type}:{key.source_object_id}"
    return _stable_id(f"brief_{key.platform.value}", source)


def _evidence_ref_id(unit: CanonicalVocUnit) -> str:
    source = f"{unit.collection_run_id}:{unit.source_object_id}"
    return _stable_id("evidence", source)


def _relation_edge_ref_id(edge: RelationEdge) -> str:
    source = (
        f"{edge.source_platform.value}:{edge.source_object_id}:"
        f"{edge.relation_type}:{edge.from_id}:{edge.to_id}"
    )
    return _stable_id("edge", source)


def _stable_id(prefix: str, source: str) -> str:
    return f"{prefix}_{sha256(source.encode('utf-8')).hexdigest()[:16]}"


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

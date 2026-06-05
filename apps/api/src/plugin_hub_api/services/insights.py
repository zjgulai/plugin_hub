from __future__ import annotations

from plugin_hub_api.schemas import CanonicalVocUnit, JsonValue

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


type TopicEvidence = dict[str, object]


def generate_strategy_notes(units: list[CanonicalVocUnit]) -> list[dict[str, JsonValue]]:
    grouped: dict[str, TopicEvidence] = {}
    for unit in units:
        topic = _topic_for_body(unit.body)
        evidence = grouped.setdefault(
            topic,
            {
                "count": 0,
                "examples": [],
                "evidence_strength": unit.coverage_confidence,
                "quality_flags": set[str](),
            },
        )
        evidence["count"] = _evidence_count(evidence) + 1
        _append_example(evidence, unit)
        evidence["evidence_strength"] = min(
            _evidence_strength(evidence),
            unit.coverage_confidence,
        )
        _quality_flags(evidence).update(unit.quality_flags)

    return [
        _strategy_note(topic=topic, evidence=evidence)
        for topic, evidence in sorted(
            grouped.items(),
            key=lambda item: (-_evidence_count(item[1]), item[0]),
        )
    ]


def _topic_for_body(body: str) -> str:
    normalized = body.lower()
    for topic, keywords in TOPIC_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return topic
    return "general"


def _append_example(evidence: TopicEvidence, unit: CanonicalVocUnit) -> None:
    examples = _examples(evidence)
    if len(examples) < 3:
        examples.append(_evidence_example(unit))


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
    evidence_examples: list[JsonValue] = [example for example in _examples(evidence)]
    quality_flags: list[JsonValue] = [flag for flag in sorted(_quality_flags(evidence))]
    return {
        "strategy_type": "voc_template",
        "topic": topic,
        "evidence_count": _evidence_count(evidence),
        "evidence_examples": evidence_examples,
        "recommendation": RECOMMENDATIONS[topic],
        "evidence_strength": float(_evidence_strength(evidence)),
        "quality_flags": quality_flags,
    }


def _evidence_count(evidence: TopicEvidence) -> int:
    value = evidence["count"]
    if not isinstance(value, int):
        raise TypeError("strategy_note_count_must_be_int")
    return value


def _examples(evidence: TopicEvidence) -> list[dict[str, JsonValue]]:
    value = evidence["examples"]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError("strategy_note_examples_must_be_objects")
    return value


def _evidence_strength(evidence: TopicEvidence) -> float:
    value = evidence["evidence_strength"]
    if not isinstance(value, float):
        raise TypeError("strategy_note_strength_must_be_float")
    return value


def _quality_flags(evidence: TopicEvidence) -> set[str]:
    value = evidence["quality_flags"]
    if not isinstance(value, set) or not all(isinstance(item, str) for item in value):
        raise TypeError("strategy_note_quality_flags_must_be_strings")
    return value

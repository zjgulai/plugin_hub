from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from plugin_hub_api.schemas import (
    AnalysisArtifactSnapshot,
    AnalysisArtifactType,
    AnalysisRunSnapshot,
    CanonicalVocUnit,
    JsonValue,
    Platform,
    ensure_json_object,
)
from plugin_hub_api.services.insights import (
    ADVISOR_PROFILE,
    GENERATION_METHOD,
    INSIGHT_TEMPLATE_BY_PLATFORM,
    INSIGHT_TEMPLATE_VERSION,
    build_voc_signal_bundle,
    generate_insight_briefs,
    generate_strategy_notes,
)

SNAPSHOT_SCHEMA_VERSION = "analysis_snapshot_v1"
SIGNAL_SCHEMA_VERSION = "enriched_voc_signal_v1"
RELATION_SCHEMA_VERSION = "relation_edge_v1"
STRATEGY_NOTE_SCHEMA_VERSION = "strategy_note_v1"
INSIGHT_BRIEF_SCHEMA_VERSION = "insight_brief_v1"


@dataclass(frozen=True)
class InsightSnapshotBuild:
    run: AnalysisRunSnapshot
    artifacts: list[AnalysisArtifactSnapshot]


def build_insight_snapshot(
    units: list[CanonicalVocUnit],
    *,
    platform: Platform,
    language: str,
    source_unit_count: int,
    source_unit_limit: int,
    truncated: bool,
    created_at: datetime | None = None,
) -> InsightSnapshotBuild:
    template_id = INSIGHT_TEMPLATE_BY_PLATFORM.get(platform)
    if template_id is None:
        raise ValueError("analysis_snapshot_platform_not_supported")
    if not units:
        raise ValueError("analysis_snapshot_requires_evidence")

    snapshot_created_at = created_at or datetime.now(tz=UTC)
    scope = ensure_json_object(
        {
            "platform": platform.value,
            "analysis_policy": "exclude_reddit_more_node",
            "source_unit_limit": source_unit_limit,
            "truncated": truncated,
        }
    )
    template_contract = ensure_json_object(
        {
            "advisor_profile": ADVISOR_PROFILE,
            "brief_template_id": template_id,
            "brief_template_version": INSIGHT_TEMPLATE_VERSION,
            "generation_method": GENERATION_METHOD,
            "signal_inference_method": "deterministic_keyword_v1",
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        }
    )
    input_digest = _digest_json(_stable_unit_payloads(units))
    run_identity = ensure_json_object(
        {
            "input_digest": input_digest,
            "language": language,
            "scope": scope,
            "template_contract": template_contract,
        }
    )
    analysis_run_id = f"analysis_{_raw_digest(run_identity)[:32]}"

    bundle = build_voc_signal_bundle(units)
    artifact_payloads: list[tuple[AnalysisArtifactType, str, str, dict[str, JsonValue]]] = []
    for edge in bundle.relation_edges:
        payload = ensure_json_object(edge.model_dump(mode="json"))
        artifact_payloads.append(
            (
                AnalysisArtifactType.RELATION_EDGE,
                f"edge_{_raw_digest(payload)[:24]}",
                RELATION_SCHEMA_VERSION,
                payload,
            )
        )
    for signal in bundle.enriched_voc_signals:
        artifact_payloads.append(
            (
                AnalysisArtifactType.ENRICHED_VOC_SIGNAL,
                signal.signal_id,
                SIGNAL_SCHEMA_VERSION,
                ensure_json_object(signal.model_dump(mode="json")),
            )
        )
    for note in generate_strategy_notes(units):
        topic = note.get("topic")
        artifact_key = (
            f"topic_{topic}" if isinstance(topic, str) else f"note_{_raw_digest(note)[:24]}"
        )
        artifact_payloads.append(
            (
                AnalysisArtifactType.STRATEGY_NOTE,
                artifact_key,
                STRATEGY_NOTE_SCHEMA_VERSION,
                note,
            )
        )
    for brief in generate_insight_briefs(
        units,
        language=language,
        limit=source_unit_limit,
        created_at=snapshot_created_at,
    ):
        artifact_payloads.append(
            (
                AnalysisArtifactType.INSIGHT_BRIEF,
                brief.brief_id,
                INSIGHT_BRIEF_SCHEMA_VERSION,
                ensure_json_object(brief.model_dump(mode="json")),
            )
        )

    artifacts = sorted(
        [
            _artifact_snapshot(
                analysis_run_id=analysis_run_id,
                artifact_type=artifact_type,
                artifact_key=artifact_key,
                schema_version=schema_version,
                payload=payload,
                created_at=snapshot_created_at,
            )
            for artifact_type, artifact_key, schema_version, payload in artifact_payloads
        ],
        key=lambda artifact: (artifact.artifact_type.value, artifact.artifact_key),
    )
    output_digest = _digest_json(
        [
            {
                "artifact_key": artifact.artifact_key,
                "artifact_type": artifact.artifact_type.value,
                "payload_digest": artifact.payload_digest,
            }
            for artifact in artifacts
        ]
    )
    collection_run_ids = sorted({unit.collection_run_id for unit in units})
    run = AnalysisRunSnapshot.model_validate(
        {
            "analysis_run_id": analysis_run_id,
            "platform": platform,
            "language": language,
            "scope": scope,
            "collection_run_ids": collection_run_ids,
            "input_digest": input_digest,
            "template_contract": template_contract,
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "generation_method": GENERATION_METHOD,
            "source_unit_count": source_unit_count,
            "analysis_unit_count": len(units),
            "truncated": truncated,
            "artifact_count": len(artifacts),
            "output_digest": output_digest,
            "created_at": snapshot_created_at,
        }
    )
    return InsightSnapshotBuild(run=run, artifacts=artifacts)


def _artifact_snapshot(
    *,
    analysis_run_id: str,
    artifact_type: AnalysisArtifactType,
    artifact_key: str,
    schema_version: str,
    payload: dict[str, JsonValue],
    created_at: datetime,
) -> AnalysisArtifactSnapshot:
    payload_digest = _digest_json(payload)
    snapshot_identity = f"{analysis_run_id}:{artifact_type.value}:{artifact_key}"
    return AnalysisArtifactSnapshot.model_validate(
        {
            "analysis_snapshot_id": (
                f"snapshot_{sha256(snapshot_identity.encode()).hexdigest()[:32]}"
            ),
            "analysis_run_id": analysis_run_id,
            "artifact_type": artifact_type,
            "artifact_key": artifact_key,
            "schema_version": schema_version,
            "payload": payload,
            "payload_digest": payload_digest,
            "created_at": created_at,
        }
    )


def _stable_unit_payloads(units: list[CanonicalVocUnit]) -> list[JsonValue]:
    payloads: list[dict[str, JsonValue]] = [
        ensure_json_object(unit.model_dump(mode="json")) for unit in units
    ]
    return sorted(payloads, key=_canonical_json)


def _digest_json(value: JsonValue) -> str:
    return f"sha256:{_raw_digest(value)}"


def _raw_digest(value: JsonValue) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: JsonValue) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from plugin_hub_api.source_urls import validate_platform_source_url

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


def ensure_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("json_value_must_be_finite")
        return value
    if isinstance(value, Decimal):
        raise ValueError("value_must_be_json_serializable")
    if isinstance(value, list):
        return [ensure_json_value(item) for item in value]
    if isinstance(value, dict):
        output: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("json_object_keys_must_be_strings")
            output[key] = ensure_json_value(item)
        return output
    raise ValueError("value_must_be_json_serializable")


def ensure_json_object(value: object) -> dict[str, JsonValue]:
    checked = ensure_json_value(value)
    if not isinstance(checked, dict):
        raise ValueError("json_object_required")
    return checked


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Platform(StrEnum):
    AMAZON = "amazon"
    REDDIT = "reddit"
    INSTAGRAM = "instagram"


class DataAssetSummary(StrictBaseModel):
    collection_run_count: int = Field(ge=0)
    raw_item_count: int = Field(ge=0)
    canonical_voc_count: int = Field(ge=0)
    analysis_eligible_voc_count: int = Field(ge=0)
    placeholder_voc_count: int = Field(ge=0)
    flagged_voc_count: int = Field(ge=0)
    low_confidence_voc_count: int = Field(ge=0)
    average_coverage_confidence: float = Field(ge=0.0, le=1.0)
    runs_with_count_mismatch: int = Field(ge=0)
    orphan_raw_count: int = Field(ge=0)
    orphan_voc_count: int = Field(ge=0)
    platform_counts: dict[str, int]
    latest_run_at: datetime | None
    latest_capture_at: datetime | None


class DataAssetRun(StrictBaseModel):
    collection_run_id: str
    platform: Platform
    capture_method: str
    stop_reason: str | None
    coverage_confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime
    first_captured_at: datetime | None
    last_captured_at: datetime | None
    raw_item_count: int = Field(ge=0)
    canonical_voc_count: int = Field(ge=0)
    analysis_eligible_voc_count: int = Field(ge=0)
    placeholder_voc_count: int = Field(ge=0)
    asset_state: Literal["complete", "empty", "mismatch"]


class SourceKind(StrEnum):
    AMAZON_REVIEW = "amazon_review"
    REDDIT_THREAD = "reddit_thread"
    REDDIT_COMMENT = "reddit_comment"
    INSTAGRAM_COMMENT = "instagram_comment"


class CollectionTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRY_SCHEDULED = "retry_scheduled"
    COMPLETED = "completed"
    FAILED = "failed"


class PlatformSettingSource(StrEnum):
    DEFAULT = "default"
    STORED = "stored"


class PlatformSetting(StrictBaseModel):
    platform: Platform
    enabled: bool
    config: dict[str, JsonValue] = Field(default_factory=dict)
    updated_at: datetime
    updated_by: str
    source: PlatformSettingSource

    @field_validator("config", mode="before")
    @classmethod
    def validate_config(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class PlatformSettingsResponse(StrictBaseModel):
    items: list[PlatformSetting]


class PlatformSettingUpdate(StrictBaseModel):
    enabled: bool | None = None
    config: dict[str, JsonValue] | None = None
    updated_by: str = Field(default="dashboard-ui", min_length=1, max_length=64)

    @field_validator("config", mode="before")
    @classmethod
    def validate_config(cls, value: object) -> dict[str, JsonValue] | None:
        if value is None:
            return None
        return ensure_json_object(value)

    @model_validator(mode="after")
    def require_update_field(self) -> PlatformSettingUpdate:
        if self.enabled is None and self.config is None:
            raise ValueError("platform_setting_update_required")
        return self


class PlatformSettingAuditEvent(StrictBaseModel):
    id: int
    platform: Platform
    changed_fields: list[str]
    previous_enabled: bool | None
    new_enabled: bool | None
    previous_config: dict[str, JsonValue] = Field(default_factory=dict)
    new_config: dict[str, JsonValue] = Field(default_factory=dict)
    changed_by: str
    created_at: datetime

    @field_validator("changed_fields", mode="before")
    @classmethod
    def validate_changed_fields(cls, value: object) -> list[str]:
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("changed_fields_string_list_required")
        return value

    @field_validator("previous_config", "new_config", mode="before")
    @classmethod
    def validate_audit_config(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class PlatformSettingAuditEventsResponse(StrictBaseModel):
    items: list[PlatformSettingAuditEvent]


class CollectionRunCreate(StrictBaseModel):
    platform: Platform
    source_url: AnyHttpUrl
    capture_method: str = Field(min_length=1, max_length=128)
    coverage_scope: dict[str, JsonValue] = Field(default_factory=dict)
    stop_reason: str | None = Field(default=None, max_length=128)
    coverage_confidence: float = Field(ge=0.0, le=1.0, strict=True)

    @field_validator("coverage_scope", mode="before")
    @classmethod
    def validate_coverage_scope(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)

    @model_validator(mode="after")
    def validate_source_provenance(self) -> CollectionRunCreate:
        validate_platform_source_url(self.platform.value, str(self.source_url))
        return self


class CollectionRun(CollectionRunCreate):
    collection_run_id: str
    created_at: datetime


class CollectionTaskCreate(StrictBaseModel):
    platform: Platform
    source_url: AnyHttpUrl
    requested_capture_method: str = Field(min_length=1, max_length=128)
    trigger_reason: str = Field(min_length=1, max_length=128)
    context: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("context", mode="before")
    @classmethod
    def validate_context(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)

    @model_validator(mode="after")
    def validate_source_target(self) -> CollectionTaskCreate:
        validate_platform_source_url(self.platform.value, str(self.source_url))
        return self


class CollectionTask(CollectionTaskCreate):
    collection_task_id: str
    status: CollectionTaskStatus
    created_at: datetime
    updated_at: datetime


class RawSourceItem(StrictBaseModel):
    platform: Platform
    source_kind: SourceKind
    source_object_id: str = Field(min_length=1, max_length=256)
    raw_schema_version: str = Field(min_length=1, max_length=128)
    parser_version: str = Field(min_length=1, max_length=128)
    raw_payload: dict[str, JsonValue]
    raw_payload_hash: str = Field(min_length=1, max_length=256)
    captured_at: datetime

    @field_validator("raw_payload", mode="before")
    @classmethod
    def validate_raw_payload(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)

    @field_validator("captured_at")
    @classmethod
    def normalize_captured_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_source_kind_platform(self) -> RawSourceItem:
        expected_platform = {
            SourceKind.AMAZON_REVIEW: Platform.AMAZON,
            SourceKind.REDDIT_THREAD: Platform.REDDIT,
            SourceKind.REDDIT_COMMENT: Platform.REDDIT,
            SourceKind.INSTAGRAM_COMMENT: Platform.INSTAGRAM,
        }[self.source_kind]
        if self.platform != expected_platform:
            raise ValueError("source_kind_platform_mismatch")
        return self


class CanonicalVocUnit(StrictBaseModel):
    platform: Platform
    source_kind: SourceKind
    source_object_id: str
    collection_run_id: str
    source_url: AnyHttpUrl
    captured_at: datetime
    created_at: datetime | None = None
    author_display: str | None = None
    author_type: str | None = None
    title: str | None = None
    body: str
    language: str | None = None
    media_refs: list[str] = Field(default_factory=list)
    commercial_object_type: str | None = None
    brand: str | None = None
    product_title: str | None = None
    asin: str | None = None
    parent_asin: str | None = None
    marketplace: str | None = None
    category: str | None = None
    thread_id: str | None = None
    parent_id: str | None = None
    depth: int | None = None
    reply_role: str | None = None
    quality_flags: list[str] = Field(default_factory=list)
    coverage_confidence: float = Field(ge=0.0, le=1.0, strict=True)
    platform_extension: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("platform_extension", mode="before")
    @classmethod
    def validate_platform_extension(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class RelationEdge(StrictBaseModel):
    source_platform: Platform
    source_kind: SourceKind
    source_object_id: str
    collection_run_id: str
    relation_type: str = Field(min_length=1, max_length=128)
    from_type: str = Field(min_length=1, max_length=128)
    from_id: str = Field(min_length=1, max_length=512)
    to_type: str = Field(min_length=1, max_length=128)
    to_id: str = Field(min_length=1, max_length=512)
    evidence_strength: float = Field(ge=0.0, le=1.0, strict=True)
    quality_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class EnrichedVocSignal(StrictBaseModel):
    signal_id: str
    platform: Platform
    source_kind: SourceKind
    source_object_id: str
    collection_run_id: str
    topic: str
    aspect: str
    pain_point: str
    severity: str
    sentiment: str | None = None
    sentiment_confidence: float | None = Field(default=None, ge=0.0, le=1.0, strict=True)
    purchase_intent: str | None = None
    usage_scenario: str | None = None
    feature_request: bool = False
    quality_issue: bool = False
    comparison_target: str | None = None
    strategy_relevance: float = Field(ge=0.0, le=1.0, strict=True)
    evidence_strength: float = Field(ge=0.0, le=1.0, strict=True)
    inference_method: str
    quality_flags: list[str] = Field(default_factory=list)
    evidence_examples: list[dict[str, JsonValue]] = Field(default_factory=list)
    relation_edges: list[RelationEdge] = Field(default_factory=list)

    @field_validator("evidence_examples", mode="before")
    @classmethod
    def validate_evidence_examples(cls, value: object) -> list[dict[str, JsonValue]]:
        if not isinstance(value, list):
            raise ValueError("evidence_examples_list_required")
        return [ensure_json_object(item) for item in value]


class VocSignalBundle(StrictBaseModel):
    relation_edges: list[RelationEdge]
    enriched_voc_signals: list[EnrichedVocSignal]


class InsightScope(StrictBaseModel):
    platform: Platform
    source_object_type: str = Field(min_length=1, max_length=128)
    source_object_id: str = Field(min_length=1, max_length=512)
    source_url: str = Field(min_length=1, max_length=2048)
    collection_run_ids: list[str]
    coverage_scope: str = Field(min_length=1, max_length=512)
    coverage_confidence: float = Field(ge=0.0, le=1.0, strict=True)


class ExecutiveFinding(StrictBaseModel):
    finding_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    business_meaning: str = Field(min_length=1, max_length=1024)
    priority: str = Field(min_length=1, max_length=16)
    confidence_level: str = Field(min_length=1, max_length=32)
    evidence_ref_ids: list[str]


class BusinessSignal(StrictBaseModel):
    signal_id: str = Field(min_length=1, max_length=128)
    signal_type: str = Field(min_length=1, max_length=128)
    topic: str = Field(min_length=1, max_length=128)
    aspect: str = Field(min_length=1, max_length=128)
    customer_language: list[str] = Field(default_factory=list)
    business_impact: str = Field(min_length=1, max_length=1024)
    severity: str = Field(min_length=1, max_length=32)
    priority: str = Field(min_length=1, max_length=16)
    evidence_strength: str = Field(min_length=1, max_length=32)
    confidence_reason: str = Field(min_length=1, max_length=1024)
    evidence_ref_ids: list[str]
    quality_flags: list[str] = Field(default_factory=list)


class ActionRecommendation(StrictBaseModel):
    action_id: str = Field(min_length=1, max_length=128)
    action_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    recommendation: str = Field(min_length=1, max_length=1024)
    why_now: str = Field(min_length=1, max_length=1024)
    expected_metric: str = Field(min_length=1, max_length=128)
    owner_role: str = Field(min_length=1, max_length=128)
    priority: str = Field(min_length=1, max_length=16)
    effort: str = Field(min_length=1, max_length=32)
    evidence_ref_ids: list[str]


class EvidenceReference(StrictBaseModel):
    evidence_ref_id: str = Field(min_length=1, max_length=128)
    voc_unit_id: str = Field(min_length=1, max_length=512)
    platform: Platform
    source_kind: SourceKind
    source_object_id: str = Field(min_length=1, max_length=512)
    quote: str
    normalized_quote: str | None = None
    rating: float | None = None
    relation_edge_ids: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    source_url: str = Field(min_length=1, max_length=2048)


class BriefConfidence(StrictBaseModel):
    level: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=1024)
    evidence_count: int = Field(ge=0)
    source_diversity: str = Field(min_length=1, max_length=128)
    coverage_notes: list[str] = Field(default_factory=list)


class DataGap(StrictBaseModel):
    gap_type: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=1024)
    recommended_collection: str = Field(min_length=1, max_length=1024)
    blocks_confidence: bool


class InsightBrief(StrictBaseModel):
    brief_id: str = Field(min_length=1, max_length=128)
    template_id: str = Field(min_length=1, max_length=128)
    template_version: str = Field(min_length=1, max_length=32)
    language: str = Field(min_length=2, max_length=16)
    advisor_profile: str = Field(min_length=1, max_length=128)
    scope: InsightScope
    headline: str = Field(min_length=1, max_length=512)
    executive_findings: list[ExecutiveFinding]
    business_signals: list[BusinessSignal]
    action_plan: list[ActionRecommendation]
    evidence_refs: list[EvidenceReference]
    confidence: BriefConfidence
    data_gaps: list[DataGap]
    generation_method: str = Field(min_length=1, max_length=128)
    created_at: datetime


class AnalysisArtifactType(StrEnum):
    RELATION_EDGE = "relation_edge"
    ENRICHED_VOC_SIGNAL = "enriched_voc_signal"
    STRATEGY_NOTE = "strategy_note"
    INSIGHT_BRIEF = "insight_brief"


class AnalysisRunSnapshot(StrictBaseModel):
    analysis_run_id: str = Field(min_length=1, max_length=128)
    platform: Platform
    language: str = Field(min_length=2, max_length=16)
    scope: dict[str, JsonValue]
    collection_run_ids: list[str]
    input_digest: str = Field(min_length=1, max_length=128)
    template_contract: dict[str, JsonValue]
    snapshot_schema_version: str = Field(min_length=1, max_length=64)
    generation_method: str = Field(min_length=1, max_length=128)
    source_unit_count: int = Field(ge=0)
    analysis_unit_count: int = Field(ge=0)
    truncated: bool
    artifact_count: int = Field(ge=0)
    output_digest: str = Field(min_length=1, max_length=128)
    created_at: datetime

    @field_validator("scope", "template_contract", mode="before")
    @classmethod
    def validate_json_objects(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class AnalysisArtifactSnapshot(StrictBaseModel):
    analysis_snapshot_id: str = Field(min_length=1, max_length=128)
    analysis_run_id: str = Field(min_length=1, max_length=128)
    artifact_type: AnalysisArtifactType
    artifact_key: str = Field(min_length=1, max_length=256)
    schema_version: str = Field(min_length=1, max_length=64)
    payload: dict[str, JsonValue]
    payload_digest: str = Field(min_length=1, max_length=128)
    created_at: datetime

    @field_validator("payload", mode="before")
    @classmethod
    def validate_payload(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class AnalysisSnapshotDetail(StrictBaseModel):
    run: AnalysisRunSnapshot
    artifacts: list[AnalysisArtifactSnapshot]

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Platform(StrEnum):
    AMAZON = "amazon"
    REDDIT = "reddit"


class SourceKind(StrEnum):
    AMAZON_REVIEW = "amazon_review"
    REDDIT_THREAD = "reddit_thread"
    REDDIT_COMMENT = "reddit_comment"


class CollectionRunCreate(StrictBaseModel):
    platform: Platform
    source_url: AnyHttpUrl
    capture_method: str
    coverage_scope: dict[str, JsonValue] = Field(default_factory=dict)
    stop_reason: str | None = None
    coverage_confidence: float = Field(ge=0.0, le=1.0, strict=True)


class CollectionRun(CollectionRunCreate):
    collection_run_id: str
    created_at: datetime


class RawSourceItem(StrictBaseModel):
    platform: Platform
    source_kind: SourceKind
    source_object_id: str
    raw_schema_version: str
    parser_version: str
    raw_payload: dict[str, JsonValue]
    raw_payload_hash: str
    captured_at: datetime


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

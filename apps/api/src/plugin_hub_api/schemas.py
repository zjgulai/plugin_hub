from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

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

    @field_validator("coverage_scope", mode="before")
    @classmethod
    def validate_coverage_scope(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


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

    @field_validator("raw_payload", mode="before")
    @classmethod
    def validate_raw_payload(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


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

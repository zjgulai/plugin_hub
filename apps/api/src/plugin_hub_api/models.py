from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from plugin_hub_api.db import Base
from plugin_hub_api.schemas import JsonValue


class CollectionRunRow(Base):
    __tablename__ = "collection_runs"

    collection_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    capture_method: Mapped[str] = mapped_column(String(128), nullable=False)
    coverage_scope: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)
    stop_reason: Mapped[str | None] = mapped_column(String(128))
    coverage_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RawSourceItemRow(Base):
    __tablename__ = "raw_source_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_run_id: Mapped[str] = mapped_column(
        ForeignKey("collection_runs.collection_run_id"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_object_id: Mapped[str] = mapped_column(String(256), nullable=False)
    raw_schema_version: Mapped[str] = mapped_column(String(128), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_payload: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)
    raw_payload_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CanonicalVocUnitRow(Base):
    __tablename__ = "canonical_voc_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_object_id: Mapped[str] = mapped_column(String(256), nullable=False)
    collection_run_id: Mapped[str] = mapped_column(
        ForeignKey("collection_runs.collection_run_id"),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_display: Mapped[str | None] = mapped_column(String(256))
    author_type: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(32))
    media_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    commercial_object_type: Mapped[str | None] = mapped_column(String(128))
    brand: Mapped[str | None] = mapped_column(String(256))
    product_title: Mapped[str | None] = mapped_column(Text)
    asin: Mapped[str | None] = mapped_column(String(32))
    parent_asin: Mapped[str | None] = mapped_column(String(32))
    marketplace: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(256))
    thread_id: Mapped[str | None] = mapped_column(String(256), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(256))
    depth: Mapped[int | None] = mapped_column(Integer)
    reply_role: Mapped[str | None] = mapped_column(String(64))
    quality_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    coverage_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    platform_extension: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)

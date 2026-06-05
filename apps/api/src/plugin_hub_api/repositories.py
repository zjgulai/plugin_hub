from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from plugin_hub_api.models import CanonicalVocUnitRow, CollectionRunRow, RawSourceItemRow
from plugin_hub_api.schemas import CanonicalVocUnit, CollectionRun, Platform, RawSourceItem


class SqlAlchemyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_collection(
        self,
        *,
        run: CollectionRun,
        raw_items: list[RawSourceItem],
        voc_units: list[CanonicalVocUnit],
    ) -> None:
        self._session.add(_collection_run_row(run))

        for raw_item in raw_items:
            self._session.add(
                RawSourceItemRow(
                    collection_run_id=run.collection_run_id,
                    platform=raw_item.platform.value,
                    source_kind=raw_item.source_kind.value,
                    source_object_id=raw_item.source_object_id,
                    raw_schema_version=raw_item.raw_schema_version,
                    parser_version=raw_item.parser_version,
                    raw_payload=raw_item.raw_payload,
                    raw_payload_hash=raw_item.raw_payload_hash,
                    captured_at=raw_item.captured_at,
                )
            )

        for voc_unit in voc_units:
            self._session.add(_canonical_voc_unit_row(voc_unit))

        self._session.commit()

    def list_voc_units(self, *, platform: Platform | None = None) -> list[CanonicalVocUnit]:
        statement = select(CanonicalVocUnitRow).order_by(CanonicalVocUnitRow.id)
        if platform is not None:
            statement = statement.where(CanonicalVocUnitRow.platform == platform.value)

        rows = self._session.scalars(statement).all()
        return [self._voc_unit_from_row(row) for row in rows]

    @staticmethod
    def _voc_unit_from_row(row: CanonicalVocUnitRow) -> CanonicalVocUnit:
        return CanonicalVocUnit.model_validate(
            {
                "platform": row.platform,
                "source_kind": row.source_kind,
                "source_object_id": row.source_object_id,
                "collection_run_id": row.collection_run_id,
                "source_url": row.source_url,
                "captured_at": row.captured_at,
                "created_at": row.created_at,
                "author_display": row.author_display,
                "author_type": row.author_type,
                "title": row.title,
                "body": row.body,
                "language": row.language,
                "media_refs": row.media_refs,
                "commercial_object_type": row.commercial_object_type,
                "brand": row.brand,
                "product_title": row.product_title,
                "asin": row.asin,
                "parent_asin": row.parent_asin,
                "marketplace": row.marketplace,
                "category": row.category,
                "thread_id": row.thread_id,
                "parent_id": row.parent_id,
                "depth": row.depth,
                "reply_role": row.reply_role,
                "quality_flags": row.quality_flags,
                "coverage_confidence": row.coverage_confidence,
                "platform_extension": row.platform_extension,
            }
        )


def _collection_run_row(run: CollectionRun) -> CollectionRunRow:
    return CollectionRunRow(
        collection_run_id=run.collection_run_id,
        platform=run.platform.value,
        source_url=str(run.model_dump(mode="json")["source_url"]),
        capture_method=run.capture_method,
        coverage_scope=run.coverage_scope,
        stop_reason=run.stop_reason,
        coverage_confidence=run.coverage_confidence,
        created_at=run.created_at,
    )


def _canonical_voc_unit_row(voc_unit: CanonicalVocUnit) -> CanonicalVocUnitRow:
    return CanonicalVocUnitRow(
        platform=voc_unit.platform.value,
        source_kind=voc_unit.source_kind.value,
        source_object_id=voc_unit.source_object_id,
        collection_run_id=voc_unit.collection_run_id,
        source_url=str(voc_unit.model_dump(mode="json")["source_url"]),
        captured_at=voc_unit.captured_at,
        created_at=voc_unit.created_at,
        author_display=voc_unit.author_display,
        author_type=voc_unit.author_type,
        title=voc_unit.title,
        body=voc_unit.body,
        language=voc_unit.language,
        media_refs=voc_unit.media_refs,
        commercial_object_type=voc_unit.commercial_object_type,
        brand=voc_unit.brand,
        product_title=voc_unit.product_title,
        asin=voc_unit.asin,
        parent_asin=voc_unit.parent_asin,
        marketplace=voc_unit.marketplace,
        category=voc_unit.category,
        thread_id=voc_unit.thread_id,
        parent_id=voc_unit.parent_id,
        depth=voc_unit.depth,
        reply_role=voc_unit.reply_role,
        quality_flags=voc_unit.quality_flags,
        coverage_confidence=voc_unit.coverage_confidence,
        platform_extension=voc_unit.platform_extension,
    )

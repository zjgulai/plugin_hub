from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from plugin_hub_api.models import (
    CanonicalVocUnitRow,
    CollectionRunRow,
    CollectionTaskRow,
    RawSourceItemRow,
)
from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    CollectionRun,
    CollectionTask,
    CollectionTaskStatus,
    Platform,
    RawSourceItem,
)


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
        try:
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
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def list_voc_units(self, *, platform: Platform | None = None) -> list[CanonicalVocUnit]:
        statement = select(CanonicalVocUnitRow).order_by(CanonicalVocUnitRow.id)
        if platform is not None:
            statement = statement.where(CanonicalVocUnitRow.platform == platform.value)

        rows = self._session.scalars(statement).all()
        return [self._voc_unit_from_row(row) for row in rows]

    def save_collection_task(self, task: CollectionTask) -> None:
        try:
            self._session.add(_collection_task_row(task))
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def list_collection_tasks(self, *, platform: Platform | None = None) -> list[CollectionTask]:
        statement = select(CollectionTaskRow).order_by(CollectionTaskRow.created_at.desc())
        if platform is not None:
            statement = statement.where(CollectionTaskRow.platform == platform.value)

        rows = self._session.scalars(statement).all()
        return [self._collection_task_from_row(row) for row in rows]

    def get_collection_task(self, collection_task_id: str) -> CollectionTask | None:
        row = self._session.get(CollectionTaskRow, collection_task_id)
        return self._collection_task_from_row(row) if row is not None else None

    def get_next_pending_collection_task(self) -> CollectionTask | None:
        return self.get_next_runnable_collection_task()

    def get_next_runnable_collection_task(
        self,
        *,
        now: datetime | None = None,
    ) -> CollectionTask | None:
        reference_time = now if now is not None else datetime.now(tz=UTC)
        row = self._session.scalars(
            select(CollectionTaskRow)
            .where(
                CollectionTaskRow.status.in_(
                    (
                        CollectionTaskStatus.PENDING.value,
                        CollectionTaskStatus.RETRY_SCHEDULED.value,
                    )
                )
            )
            .order_by(CollectionTaskRow.created_at)
        ).all()
        for candidate in (self._collection_task_from_row(candidate_row) for candidate_row in row):
            if _collection_task_is_runnable(candidate, reference_time):
                return candidate
        return None

    def claim_next_runnable_collection_task(
        self,
        *,
        worker_id: str,
        claim_ttl_seconds: int,
        now: datetime | None = None,
    ) -> CollectionTask | None:
        reference_time = now if now is not None else datetime.now(tz=UTC)
        claim_expires_at = reference_time + timedelta(seconds=max(claim_ttl_seconds, 0))
        rows = self._session.scalars(
            select(CollectionTaskRow).order_by(CollectionTaskRow.created_at)
        ).all()
        try:
            for row in rows:
                task = self._collection_task_from_row(row)
                if not _collection_task_is_claimable(task, reference_time):
                    continue

                claimed_task = task.model_copy(
                    update={
                        "status": CollectionTaskStatus.RUNNING,
                        "updated_at": reference_time,
                        "context": {
                            **task.context,
                            "claimed_by": worker_id,
                            "claimed_at": reference_time.isoformat(),
                            "claim_expires_at": claim_expires_at.isoformat(),
                        },
                    }
                )
                _update_collection_task_row(row, claimed_task)
                self._session.commit()
                return claimed_task
            return None
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def update_collection_task(self, task: CollectionTask) -> None:
        try:
            row = self._session.get(CollectionTaskRow, task.collection_task_id)
            if row is None:
                return
            _update_collection_task_row(row, task)
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def save_collection_and_update_task(
        self,
        *,
        run: CollectionRun,
        raw_items: list[RawSourceItem],
        voc_units: list[CanonicalVocUnit],
        task: CollectionTask,
    ) -> None:
        try:
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

            row = self._session.get(CollectionTaskRow, task.collection_task_id)
            if row is not None:
                _update_collection_task_row(row, task)

            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise

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

    @staticmethod
    def _collection_task_from_row(row: CollectionTaskRow) -> CollectionTask:
        return CollectionTask.model_validate(
            {
                "collection_task_id": row.collection_task_id,
                "platform": row.platform,
                "source_url": row.source_url,
                "requested_capture_method": row.requested_capture_method,
                "trigger_reason": row.trigger_reason,
                "status": row.status,
                "context": row.context,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
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


def _collection_task_row(task: CollectionTask) -> CollectionTaskRow:
    return CollectionTaskRow(
        collection_task_id=task.collection_task_id,
        platform=task.platform.value,
        source_url=str(task.model_dump(mode="json")["source_url"]),
        requested_capture_method=task.requested_capture_method,
        trigger_reason=task.trigger_reason,
        status=task.status.value,
        context=task.context,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _update_collection_task_row(row: CollectionTaskRow, task: CollectionTask) -> None:
    row.platform = task.platform.value
    row.source_url = str(task.model_dump(mode="json")["source_url"])
    row.requested_capture_method = task.requested_capture_method
    row.trigger_reason = task.trigger_reason
    row.status = task.status.value
    row.context = task.context
    row.created_at = task.created_at
    row.updated_at = task.updated_at


def _collection_task_is_runnable(task: CollectionTask, reference_time: datetime) -> bool:
    if task.status == CollectionTaskStatus.PENDING:
        return True
    if task.status != CollectionTaskStatus.RETRY_SCHEDULED:
        return False

    next_run_at = task.context.get("next_run_at")
    if not isinstance(next_run_at, str):
        return True
    try:
        parsed_next_run_at = datetime.fromisoformat(next_run_at)
    except ValueError:
        return True
    if parsed_next_run_at.tzinfo is None:
        parsed_next_run_at = parsed_next_run_at.replace(tzinfo=UTC)

    return parsed_next_run_at <= reference_time


def _collection_task_is_claimable(task: CollectionTask, reference_time: datetime) -> bool:
    if task.status == CollectionTaskStatus.RUNNING:
        return _is_running_task_stale(task, reference_time)
    return _collection_task_is_runnable(task, reference_time)


def _is_running_task_stale(task: CollectionTask, reference_time: datetime) -> bool:
    claim_expires_at = task.context.get("claim_expires_at")
    if not isinstance(claim_expires_at, str):
        return True
    parsed_claim_expires_at = _parse_iso_datetime(claim_expires_at)
    if parsed_claim_expires_at is None:
        return True
    if parsed_claim_expires_at.tzinfo is None:
        parsed_claim_expires_at = parsed_claim_expires_at.replace(tzinfo=UTC)
    return parsed_claim_expires_at <= reference_time


def _parse_iso_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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

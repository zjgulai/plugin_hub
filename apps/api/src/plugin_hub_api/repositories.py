from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from plugin_hub_api.models import (
    CanonicalVocUnitRow,
    CollectionRunRow,
    CollectionTaskRow,
    PlatformSettingAuditEventRow,
    PlatformSettingRow,
    RawSourceItemRow,
)
from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    CollectionRun,
    CollectionRunCreate,
    CollectionTask,
    CollectionTaskStatus,
    DataAssetRun,
    DataAssetSummary,
    Platform,
    PlatformSetting,
    PlatformSettingAuditEvent,
    PlatformSettingSource,
    RawSourceItem,
)


@dataclass(frozen=True)
class CollectionReplayState:
    matches_payload: bool
    raw_item_count: int
    voc_unit_count: int


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
            self._session.flush()

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

    def list_voc_units(
        self,
        *,
        platform: Platform | None = None,
        limit: int | None = None,
        offset: int = 0,
        newest_first: bool = False,
    ) -> list[CanonicalVocUnit]:
        order = CanonicalVocUnitRow.id.desc() if newest_first else CanonicalVocUnitRow.id
        statement = select(CanonicalVocUnitRow).order_by(order)
        if platform is not None:
            statement = statement.where(CanonicalVocUnitRow.platform == platform.value)
        if limit is not None:
            statement = statement.limit(limit).offset(offset)

        rows = self._session.scalars(statement).all()
        return [self._voc_unit_from_row(row) for row in rows]

    def count_voc_units(self, *, platform: Platform | None = None) -> int:
        statement = select(func.count()).select_from(CanonicalVocUnitRow)
        if platform is not None:
            statement = statement.where(CanonicalVocUnitRow.platform == platform.value)
        return int(self._session.scalar(statement) or 0)

    def get_collection_replay_state(
        self,
        *,
        collection_run_id: str,
        run: CollectionRunCreate,
        raw_items: list[RawSourceItem],
    ) -> CollectionReplayState | None:
        run_row = self._session.get(CollectionRunRow, collection_run_id)
        if run_row is None:
            return None
        raw_rows = self._session.scalars(
            select(RawSourceItemRow).where(
                RawSourceItemRow.collection_run_id == collection_run_id
            )
        ).all()
        voc_count = int(
            self._session.scalar(
                select(func.count())
                .select_from(CanonicalVocUnitRow)
                .where(CanonicalVocUnitRow.collection_run_id == collection_run_id)
            )
            or 0
        )
        run_json = run.model_dump(mode="json")
        run_matches = (
            run_row.platform == run.platform.value
            and run_row.source_url == str(run_json["source_url"])
            and run_row.capture_method == run.capture_method
            and run_row.coverage_scope == run.coverage_scope
            and run_row.stop_reason == run.stop_reason
            and run_row.coverage_confidence == run.coverage_confidence
        )
        stored_signatures = sorted(_raw_row_signature(item) for item in raw_rows)
        incoming_signatures = sorted(_raw_item_signature(item) for item in raw_items)
        return CollectionReplayState(
            matches_payload=(
                run_matches
                and stored_signatures == incoming_signatures
                and voc_count == len(raw_items)
            ),
            raw_item_count=len(raw_rows),
            voc_unit_count=voc_count,
        )

    def get_data_asset_summary(self, *, low_confidence_threshold: float) -> DataAssetSummary:
        collection_run_count = int(
            self._session.scalar(select(func.count()).select_from(CollectionRunRow)) or 0
        )
        raw_item_count = int(
            self._session.scalar(select(func.count()).select_from(RawSourceItemRow)) or 0
        )
        canonical_voc_count = int(
            self._session.scalar(select(func.count()).select_from(CanonicalVocUnitRow)) or 0
        )
        placeholder_voc_count = self._text_count(
            """
            SELECT COUNT(*)
            FROM canonical_voc_units AS unit
            WHERE EXISTS (
                SELECT 1
                FROM json_each(unit.quality_flags) AS flag
                WHERE flag.value = 'reddit_more_node'
            )
            """
        )
        platform_rows = self._session.execute(
            text(
                """
                SELECT unit.platform, COUNT(*)
                FROM canonical_voc_units AS unit
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM json_each(unit.quality_flags) AS flag
                    WHERE flag.value = 'reddit_more_node'
                )
                GROUP BY unit.platform
                """
            )
        ).all()
        platform_counts = {platform.value: 0 for platform in Platform}
        platform_counts.update({str(platform): int(count) for platform, count in platform_rows})
        latest_run_at = self._session.scalar(select(func.max(CollectionRunRow.created_at)))
        latest_capture_at = self._session.scalar(select(func.max(CanonicalVocUnitRow.captured_at)))
        eligible_predicate = """
            NOT EXISTS (
                SELECT 1
                FROM json_each(unit.quality_flags) AS flag
                WHERE flag.value = 'reddit_more_node'
            )
        """
        flagged_voc_count = self._text_count(
            f"""
            SELECT COUNT(*)
            FROM canonical_voc_units AS unit
            WHERE {eligible_predicate}
              AND json_array_length(unit.quality_flags) > 0
            """
        )
        low_confidence_voc_count = int(
            self._session.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM canonical_voc_units AS unit
                    WHERE {eligible_predicate}
                      AND unit.coverage_confidence < :threshold
                    """
                ),
                {"threshold": low_confidence_threshold},
            ).scalar_one()
        )
        average_coverage_confidence = float(
            self._session.execute(
                text(
                    f"""
                    SELECT COALESCE(AVG(unit.coverage_confidence), 0.0)
                    FROM canonical_voc_units AS unit
                    WHERE {eligible_predicate}
                    """
                )
            ).scalar_one()
        )

        return DataAssetSummary(
            collection_run_count=collection_run_count,
            raw_item_count=raw_item_count,
            canonical_voc_count=canonical_voc_count,
            analysis_eligible_voc_count=canonical_voc_count - placeholder_voc_count,
            placeholder_voc_count=placeholder_voc_count,
            flagged_voc_count=flagged_voc_count,
            low_confidence_voc_count=low_confidence_voc_count,
            average_coverage_confidence=round(average_coverage_confidence, 6),
            runs_with_count_mismatch=self._text_count(
                """
                SELECT COUNT(*)
                FROM collection_runs AS run
                LEFT JOIN (
                    SELECT collection_run_id, COUNT(*) AS item_count
                    FROM raw_source_items
                    GROUP BY collection_run_id
                ) AS raw ON raw.collection_run_id = run.collection_run_id
                LEFT JOIN (
                    SELECT collection_run_id, COUNT(*) AS item_count
                    FROM canonical_voc_units
                    GROUP BY collection_run_id
                ) AS voc ON voc.collection_run_id = run.collection_run_id
                WHERE COALESCE(raw.item_count, 0) <> COALESCE(voc.item_count, 0)
                """
            ),
            orphan_raw_count=self._text_count(
                """
                SELECT COUNT(*)
                FROM raw_source_items AS item
                LEFT JOIN collection_runs AS run
                  ON run.collection_run_id = item.collection_run_id
                WHERE run.collection_run_id IS NULL
                """
            ),
            orphan_voc_count=self._text_count(
                """
                SELECT COUNT(*)
                FROM canonical_voc_units AS item
                LEFT JOIN collection_runs AS run
                  ON run.collection_run_id = item.collection_run_id
                WHERE run.collection_run_id IS NULL
                """
            ),
            platform_counts=platform_counts,
            latest_run_at=latest_run_at,
            latest_capture_at=latest_capture_at,
        )

    def list_data_asset_runs(self, *, limit: int, offset: int) -> list[DataAssetRun]:
        rows = self._session.execute(
            text(
                """
                SELECT
                    run.collection_run_id,
                    run.platform,
                    run.capture_method,
                    run.stop_reason,
                    run.coverage_confidence,
                    run.created_at,
                    voc.first_captured_at,
                    voc.last_captured_at,
                    COALESCE(raw.item_count, 0) AS raw_item_count,
                    COALESCE(voc.item_count, 0) AS canonical_voc_count,
                    COALESCE(voc.analysis_item_count, 0) AS analysis_eligible_voc_count,
                    COALESCE(voc.placeholder_count, 0) AS placeholder_voc_count
                FROM collection_runs AS run
                LEFT JOIN (
                    SELECT collection_run_id, COUNT(*) AS item_count
                    FROM raw_source_items
                    GROUP BY collection_run_id
                ) AS raw ON raw.collection_run_id = run.collection_run_id
                LEFT JOIN (
                    SELECT
                        unit.collection_run_id,
                        COUNT(*) AS item_count,
                        SUM(
                            CASE WHEN EXISTS (
                                SELECT 1
                                FROM json_each(unit.quality_flags) AS flag
                                WHERE flag.value = 'reddit_more_node'
                            ) THEN 0 ELSE 1 END
                        ) AS analysis_item_count,
                        SUM(
                            CASE WHEN EXISTS (
                                SELECT 1
                                FROM json_each(unit.quality_flags) AS flag
                                WHERE flag.value = 'reddit_more_node'
                            ) THEN 1 ELSE 0 END
                        ) AS placeholder_count,
                        MIN(unit.captured_at) AS first_captured_at,
                        MAX(unit.captured_at) AS last_captured_at
                    FROM canonical_voc_units AS unit
                    GROUP BY unit.collection_run_id
                ) AS voc ON voc.collection_run_id = run.collection_run_id
                ORDER BY run.created_at DESC, run.collection_run_id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"limit": limit, "offset": offset},
        ).mappings()

        output: list[DataAssetRun] = []
        for row in rows:
            raw_count = int(row["raw_item_count"])
            voc_count = int(row["canonical_voc_count"])
            if raw_count != voc_count:
                state = "mismatch"
            elif raw_count == 0:
                state = "empty"
            else:
                state = "complete"
            output.append(
                DataAssetRun.model_validate(
                    {
                        **dict(row),
                        "asset_state": state,
                    }
                )
            )
        return output

    def count_collection_runs(self) -> int:
        return int(self._session.scalar(select(func.count()).select_from(CollectionRunRow)) or 0)

    def _text_count(self, statement: str) -> int:
        return int(self._session.execute(text(statement)).scalar_one())

    def save_collection_task(self, task: CollectionTask) -> None:
        try:
            self._session.add(_collection_task_row(task))
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def list_collection_tasks(
        self,
        *,
        platform: Platform | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[CollectionTask]:
        statement = select(CollectionTaskRow).order_by(CollectionTaskRow.created_at.desc())
        if platform is not None:
            statement = statement.where(CollectionTaskRow.platform == platform.value)
        if limit is not None:
            statement = statement.limit(limit).offset(offset)

        rows = self._session.scalars(statement).all()
        return [self._collection_task_from_row(row) for row in rows]

    def count_collection_tasks(self, *, platform: Platform | None = None) -> int:
        statement = select(func.count()).select_from(CollectionTaskRow)
        if platform is not None:
            statement = statement.where(CollectionTaskRow.platform == platform.value)
        return int(self._session.scalar(statement) or 0)

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

    def list_platform_settings(self) -> list[PlatformSetting]:
        rows = self._session.scalars(select(PlatformSettingRow)).all()
        return [self._platform_setting_from_row(row) for row in rows]

    def get_platform_setting(self, platform: Platform) -> PlatformSetting | None:
        row = self._session.get(PlatformSettingRow, platform.value)
        return self._platform_setting_from_row(row) if row is not None else None

    def save_platform_setting(
        self,
        *,
        setting: PlatformSetting,
        previous_setting: PlatformSetting,
        changed_fields: list[str],
    ) -> None:
        try:
            row = self._session.get(PlatformSettingRow, setting.platform.value)
            if row is None:
                self._session.add(_platform_setting_row(setting))
            else:
                _update_platform_setting_row(row, setting)

            self._session.add(
                PlatformSettingAuditEventRow(
                    platform=setting.platform.value,
                    changed_fields=changed_fields,
                    previous_enabled=previous_setting.enabled,
                    new_enabled=setting.enabled,
                    previous_config=previous_setting.config,
                    new_config=setting.config,
                    changed_by=setting.updated_by,
                    created_at=setting.updated_at,
                )
            )
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def list_platform_setting_audit_events(
        self,
        platform: Platform,
        *,
        limit: int = 20,
    ) -> list[PlatformSettingAuditEvent]:
        rows = self._session.scalars(
            select(PlatformSettingAuditEventRow)
            .where(PlatformSettingAuditEventRow.platform == platform.value)
            .order_by(PlatformSettingAuditEventRow.id.desc())
            .limit(limit)
        ).all()
        return [self._platform_setting_audit_event_from_row(row) for row in rows]

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
            self._session.flush()

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

    @staticmethod
    def _platform_setting_from_row(row: PlatformSettingRow) -> PlatformSetting:
        return PlatformSetting.model_validate(
            {
                "platform": row.platform,
                "enabled": row.enabled,
                "config": row.config,
                "updated_at": row.updated_at,
                "updated_by": row.updated_by,
                "source": PlatformSettingSource.STORED,
            }
        )

    @staticmethod
    def _platform_setting_audit_event_from_row(
        row: PlatformSettingAuditEventRow,
    ) -> PlatformSettingAuditEvent:
        return PlatformSettingAuditEvent.model_validate(
            {
                "id": row.id,
                "platform": row.platform,
                "changed_fields": row.changed_fields,
                "previous_enabled": row.previous_enabled,
                "new_enabled": row.new_enabled,
                "previous_config": row.previous_config,
                "new_config": row.new_config,
                "changed_by": row.changed_by,
                "created_at": row.created_at,
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


def _platform_setting_row(setting: PlatformSetting) -> PlatformSettingRow:
    return PlatformSettingRow(
        platform=setting.platform.value,
        enabled=setting.enabled,
        config=setting.config,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by,
    )


def _update_platform_setting_row(row: PlatformSettingRow, setting: PlatformSetting) -> None:
    row.enabled = setting.enabled
    row.config = setting.config
    row.updated_at = setting.updated_at
    row.updated_by = setting.updated_by


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


def _raw_row_signature(row: RawSourceItemRow) -> tuple[str, ...]:
    return (
        row.platform,
        row.source_kind,
        row.source_object_id,
        row.raw_schema_version,
        row.parser_version,
        _stable_json(row.raw_payload),
        row.raw_payload_hash,
        _datetime_signature(row.captured_at),
    )


def _raw_item_signature(item: RawSourceItem) -> tuple[str, ...]:
    return (
        item.platform.value,
        item.source_kind.value,
        item.source_object_id,
        item.raw_schema_version,
        item.parser_version,
        _stable_json(item.raw_payload),
        item.raw_payload_hash,
        _datetime_signature(item.captured_at),
    )


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _datetime_signature(value: datetime) -> str:
    normalized = value
    if normalized.tzinfo is not None:
        normalized = normalized.astimezone(UTC).replace(tzinfo=None)
    return normalized.isoformat(timespec="microseconds")

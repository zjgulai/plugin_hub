from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from plugin_hub_api.migrations import ANALYSIS_SNAPSHOT_MIGRATION_VERSION
from plugin_hub_api.schemas import (
    AnalysisArtifactSnapshot,
    AnalysisRunSnapshot,
    AnalysisSnapshotDetail,
    JsonValue,
    Platform,
    ensure_json_object,
    ensure_json_value,
)


class AnalysisSnapshotSchemaNotReady(RuntimeError):
    pass


class InsightSnapshotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def require_schema_ready(self) -> None:
        self._require_schema()

    def save_snapshot(
        self,
        *,
        run: AnalysisRunSnapshot,
        artifacts: list[AnalysisArtifactSnapshot],
    ) -> bool:
        self._require_schema()
        if self.get_run(run.analysis_run_id) is not None:
            return True
        try:
            self._session.execute(
                text(
                    """
                    INSERT INTO analysis_runs (
                        analysis_run_id, platform, language, scope_json,
                        collection_run_ids_json, input_digest, template_contract_json,
                        snapshot_schema_version, generation_method, source_unit_count,
                        analysis_unit_count, truncated, artifact_count, output_digest,
                        created_at
                    ) VALUES (
                        :analysis_run_id, :platform, :language, :scope_json,
                        :collection_run_ids_json, :input_digest, :template_contract_json,
                        :snapshot_schema_version, :generation_method, :source_unit_count,
                        :analysis_unit_count, :truncated, :artifact_count, :output_digest,
                        :created_at
                    )
                    """
                ),
                _run_parameters(run),
            )
            for artifact in artifacts:
                self._session.execute(
                    text(
                        """
                        INSERT INTO analysis_artifact_snapshots (
                            analysis_snapshot_id, analysis_run_id, artifact_type,
                            artifact_key, schema_version, payload_json, payload_digest,
                            created_at
                        ) VALUES (
                            :analysis_snapshot_id, :analysis_run_id, :artifact_type,
                            :artifact_key, :schema_version, :payload_json, :payload_digest,
                            :created_at
                        )
                        """
                    ),
                    _artifact_parameters(artifact),
                )
            self._session.commit()
            return False
        except IntegrityError:
            self._session.rollback()
            if self.get_run(run.analysis_run_id) is not None:
                return True
            raise
        except SQLAlchemyError:
            self._session.rollback()
            raise

    def get_run(self, analysis_run_id: str) -> AnalysisRunSnapshot | None:
        self._require_schema()
        row = (
            self._session.execute(
                text(
                    """
                SELECT * FROM analysis_runs
                WHERE analysis_run_id = :analysis_run_id
                """
                ),
                {"analysis_run_id": analysis_run_id},
            )
            .mappings()
            .one_or_none()
        )
        return _run_from_row(row) if row is not None else None

    def list_runs(
        self,
        *,
        platform: Platform | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AnalysisRunSnapshot], int]:
        self._require_schema()
        filters = ""
        parameters: dict[str, object] = {"limit": limit, "offset": offset}
        if platform is not None:
            filters = "WHERE platform = :platform"
            parameters["platform"] = platform.value
        rows = (
            self._session.execute(
                text(
                    f"""
                SELECT * FROM analysis_runs
                {filters}
                ORDER BY created_at DESC, analysis_run_id DESC
                LIMIT :limit OFFSET :offset
                """
                ),
                parameters,
            )
            .mappings()
            .all()
        )
        total = int(
            self._session.execute(
                text(f"SELECT COUNT(*) FROM analysis_runs {filters}"),
                {key: value for key, value in parameters.items() if key == "platform"},
            ).scalar_one()
        )
        return [_run_from_row(row) for row in rows], total

    def get_detail(self, analysis_run_id: str) -> AnalysisSnapshotDetail | None:
        run = self.get_run(analysis_run_id)
        if run is None:
            return None
        rows = (
            self._session.execute(
                text(
                    """
                SELECT * FROM analysis_artifact_snapshots
                WHERE analysis_run_id = :analysis_run_id
                ORDER BY artifact_type, artifact_key
                """
                ),
                {"analysis_run_id": analysis_run_id},
            )
            .mappings()
            .all()
        )
        return AnalysisSnapshotDetail(
            run=run,
            artifacts=[_artifact_from_row(row) for row in rows],
        )

    def _require_schema(self) -> None:
        try:
            exists = self._session.execute(
                text(
                    """
                    SELECT 1 FROM schema_migrations
                    WHERE version = :version
                    """
                ),
                {"version": ANALYSIS_SNAPSHOT_MIGRATION_VERSION},
            ).scalar_one_or_none()
        except OperationalError as error:
            self._session.rollback()
            raise AnalysisSnapshotSchemaNotReady("analysis_snapshot_schema_not_ready") from error
        if exists is None:
            raise AnalysisSnapshotSchemaNotReady("analysis_snapshot_schema_not_ready")


def _run_parameters(run: AnalysisRunSnapshot) -> dict[str, object]:
    return {
        "analysis_run_id": run.analysis_run_id,
        "platform": run.platform.value,
        "language": run.language,
        "scope_json": _json(run.scope),
        "collection_run_ids_json": _json(run.collection_run_ids),
        "input_digest": run.input_digest,
        "template_contract_json": _json(run.template_contract),
        "snapshot_schema_version": run.snapshot_schema_version,
        "generation_method": run.generation_method,
        "source_unit_count": run.source_unit_count,
        "analysis_unit_count": run.analysis_unit_count,
        "truncated": int(run.truncated),
        "artifact_count": run.artifact_count,
        "output_digest": run.output_digest,
        "created_at": run.created_at.isoformat(),
    }


def _artifact_parameters(artifact: AnalysisArtifactSnapshot) -> dict[str, object]:
    return {
        "analysis_snapshot_id": artifact.analysis_snapshot_id,
        "analysis_run_id": artifact.analysis_run_id,
        "artifact_type": artifact.artifact_type.value,
        "artifact_key": artifact.artifact_key,
        "schema_version": artifact.schema_version,
        "payload_json": _json(artifact.payload),
        "payload_digest": artifact.payload_digest,
        "created_at": artifact.created_at.isoformat(),
    }


def _run_from_row(row: RowMapping) -> AnalysisRunSnapshot:
    return AnalysisRunSnapshot.model_validate(
        {
            "analysis_run_id": row["analysis_run_id"],
            "platform": row["platform"],
            "language": row["language"],
            "scope": _json_object(row["scope_json"]),
            "collection_run_ids": _json_list(row["collection_run_ids_json"]),
            "input_digest": row["input_digest"],
            "template_contract": _json_object(row["template_contract_json"]),
            "snapshot_schema_version": row["snapshot_schema_version"],
            "generation_method": row["generation_method"],
            "source_unit_count": row["source_unit_count"],
            "analysis_unit_count": row["analysis_unit_count"],
            "truncated": bool(row["truncated"]),
            "artifact_count": row["artifact_count"],
            "output_digest": row["output_digest"],
            "created_at": row["created_at"],
        }
    )


def _artifact_from_row(row: RowMapping) -> AnalysisArtifactSnapshot:
    return AnalysisArtifactSnapshot.model_validate(
        {
            "analysis_snapshot_id": row["analysis_snapshot_id"],
            "analysis_run_id": row["analysis_run_id"],
            "artifact_type": row["artifact_type"],
            "artifact_key": row["artifact_key"],
            "schema_version": row["schema_version"],
            "payload": _json_object(row["payload_json"]),
            "payload_digest": row["payload_digest"],
            "created_at": row["created_at"],
        }
    )


def _json(value: object) -> str:
    checked = ensure_json_value(value)
    return json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _json_object(value: object) -> dict[str, JsonValue]:
    parsed = json.loads(str(value))
    return ensure_json_object(parsed)


def _json_list(value: object) -> list[str]:
    parsed = json.loads(str(value))
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("analysis_collection_run_ids_invalid")
    return parsed

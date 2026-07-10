from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from plugin_hub_api.insight_snapshot_repository import (
    AnalysisSnapshotSchemaNotReady,
    InsightSnapshotRepository,
)
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository, get_session
from plugin_hub_api.schemas import (
    AnalysisRunSnapshot,
    AnalysisSnapshotDetail,
    CanonicalVocUnit,
    EnrichedVocSignal,
    InsightBrief,
    JsonValue,
    Platform,
    RelationEdge,
    StrictBaseModel,
)
from plugin_hub_api.services.insight_snapshots import build_insight_snapshot
from plugin_hub_api.services.insights import (
    build_voc_signal_bundle,
    generate_insight_briefs,
    generate_strategy_notes,
)

router = APIRouter()
INSIGHT_SOURCE_UNIT_LIMIT = 2_000


class StrategyNotesResponse(StrictBaseModel):
    items: list[dict[str, JsonValue]]
    source_unit_count: int
    analysis_unit_count: int
    source_unit_limit: int
    truncated: bool


class InsightBriefsResponse(StrictBaseModel):
    items: list[InsightBrief]
    source_unit_count: int
    analysis_unit_count: int
    source_unit_limit: int
    truncated: bool


class VocSignalsResponse(StrictBaseModel):
    relation_edges: list[RelationEdge]
    enriched_voc_signals: list[EnrichedVocSignal]
    source_unit_count: int
    analysis_unit_count: int
    source_unit_limit: int
    truncated: bool


class AnalysisSnapshotCreateRequest(StrictBaseModel):
    platform: Platform
    language: str = "zh-CN"


class AnalysisSnapshotCreateResponse(StrictBaseModel):
    run: AnalysisRunSnapshot
    replayed: bool


class AnalysisSnapshotListResponse(StrictBaseModel):
    items: list[AnalysisRunSnapshot]
    total: int
    limit: int
    offset: int


def get_insight_snapshot_repository(
    session: Annotated[Session, Depends(get_session)],
) -> InsightSnapshotRepository:
    return InsightSnapshotRepository(session)


@router.get("/strategy-notes", response_model=StrategyNotesResponse)
def list_strategy_notes(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
) -> StrategyNotesResponse:
    units, total = bounded_analysis_units(repository, platform)
    return StrategyNotesResponse(
        items=generate_strategy_notes(units),
        source_unit_count=total,
        analysis_unit_count=len(units),
        source_unit_limit=INSIGHT_SOURCE_UNIT_LIMIT,
        truncated=total > INSIGHT_SOURCE_UNIT_LIMIT,
    )


@router.get("/voc-signals", response_model=VocSignalsResponse)
def list_voc_signals(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
) -> VocSignalsResponse:
    units, total = bounded_analysis_units(repository, platform)
    bundle = build_voc_signal_bundle(units)
    return VocSignalsResponse(
        relation_edges=bundle.relation_edges,
        enriched_voc_signals=bundle.enriched_voc_signals,
        source_unit_count=total,
        analysis_unit_count=len(units),
        source_unit_limit=INSIGHT_SOURCE_UNIT_LIMIT,
        truncated=total > INSIGHT_SOURCE_UNIT_LIMIT,
    )


@router.get("/briefs", response_model=InsightBriefsResponse)
def list_insight_briefs(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
    source_object_type: str | None = None,
    source_object_id: str | None = None,
    language: str = "zh-CN",
    template_id: str | None = None,
    limit: int = 20,
) -> InsightBriefsResponse:
    units, total = bounded_analysis_units(repository, platform)
    return InsightBriefsResponse(
        items=generate_insight_briefs(
            units,
            language=language,
            template_id=template_id,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            limit=limit,
        ),
        source_unit_count=total,
        analysis_unit_count=len(units),
        source_unit_limit=INSIGHT_SOURCE_UNIT_LIMIT,
        truncated=total > INSIGHT_SOURCE_UNIT_LIMIT,
    )


@router.post(
    "/snapshots",
    response_model=AnalysisSnapshotCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_snapshot(
    payload: AnalysisSnapshotCreateRequest,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    snapshot_repository: Annotated[
        InsightSnapshotRepository,
        Depends(get_insight_snapshot_repository),
    ],
) -> AnalysisSnapshotCreateResponse:
    try:
        snapshot_repository.require_schema_ready()
        units, total = bounded_analysis_units(repository, payload.platform)
        build = build_insight_snapshot(
            units,
            platform=payload.platform,
            language=payload.language,
            source_unit_count=total,
            source_unit_limit=INSIGHT_SOURCE_UNIT_LIMIT,
            truncated=total > INSIGHT_SOURCE_UNIT_LIMIT,
        )
        replayed = snapshot_repository.save_snapshot(
            run=build.run,
            artifacts=build.artifacts,
        )
        run = snapshot_repository.get_run(build.run.analysis_run_id)
    except AnalysisSnapshotSchemaNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if run is None:
        raise HTTPException(status_code=500, detail="analysis_snapshot_persistence_failed")
    return AnalysisSnapshotCreateResponse(run=run, replayed=replayed)


@router.get("/snapshots", response_model=AnalysisSnapshotListResponse)
def list_analysis_snapshots(
    session: Annotated[Session, Depends(get_session)],
    platform: Platform | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AnalysisSnapshotListResponse:
    repository = InsightSnapshotRepository(session)
    try:
        items, total = repository.list_runs(
            platform=platform,
            limit=limit,
            offset=offset,
        )
    except AnalysisSnapshotSchemaNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return AnalysisSnapshotListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/snapshots/{analysis_run_id}", response_model=AnalysisSnapshotDetail)
def get_analysis_snapshot(
    analysis_run_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> AnalysisSnapshotDetail:
    repository = InsightSnapshotRepository(session)
    try:
        detail = repository.get_detail(analysis_run_id)
    except AnalysisSnapshotSchemaNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if detail is None:
        raise HTTPException(status_code=404, detail="analysis_snapshot_not_found")
    return detail


def bounded_analysis_units(
    repository: SqlAlchemyRepository,
    platform: Platform | None,
) -> tuple[list[CanonicalVocUnit], int]:
    total = repository.count_voc_units(platform=platform)
    newest_units = repository.list_voc_units(
        platform=platform,
        limit=INSIGHT_SOURCE_UNIT_LIMIT,
        newest_first=True,
    )
    units = [
        unit for unit in reversed(newest_units) if "reddit_more_node" not in unit.quality_flags
    ]
    return units, total

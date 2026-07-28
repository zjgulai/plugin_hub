from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository
from plugin_hub_api.schemas import DataAssetRun, DataAssetSummary, StrictBaseModel

router = APIRouter()


class DataAssetRunsResponse(StrictBaseModel):
    items: list[DataAssetRun]
    total: int
    limit: int
    offset: int


@router.get("/data-assets/summary", response_model=DataAssetSummary)
def get_data_asset_summary(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    low_confidence_threshold: float = Query(default=0.7, ge=0.0, le=1.0),
) -> DataAssetSummary:
    return repository.get_data_asset_summary(
        low_confidence_threshold=low_confidence_threshold,
    )


@router.get("/data-assets/runs", response_model=DataAssetRunsResponse)
def list_data_asset_runs(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DataAssetRunsResponse:
    repository.begin_read_snapshot()
    return DataAssetRunsResponse(
        items=repository.list_data_asset_runs(limit=limit, offset=offset),
        total=repository.count_collection_runs(),
        limit=limit,
        offset=offset,
    )

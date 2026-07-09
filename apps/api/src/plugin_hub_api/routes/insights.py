from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository
from plugin_hub_api.schemas import (
    InsightBrief,
    JsonValue,
    Platform,
    StrictBaseModel,
    VocSignalBundle,
)
from plugin_hub_api.services.insights import (
    build_voc_signal_bundle,
    generate_insight_briefs,
    generate_strategy_notes,
)

router = APIRouter()


class StrategyNotesResponse(StrictBaseModel):
    items: list[dict[str, JsonValue]]


class InsightBriefsResponse(StrictBaseModel):
    items: list[InsightBrief]


@router.get("/strategy-notes", response_model=StrategyNotesResponse)
def list_strategy_notes(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
) -> StrategyNotesResponse:
    units = repository.list_voc_units(platform=platform)
    return StrategyNotesResponse(items=generate_strategy_notes(units))


@router.get("/voc-signals", response_model=VocSignalBundle)
def list_voc_signals(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
) -> VocSignalBundle:
    units = repository.list_voc_units(platform=platform)
    return build_voc_signal_bundle(units)


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
    units = repository.list_voc_units(platform=platform)
    return InsightBriefsResponse(
        items=generate_insight_briefs(
            units,
            language=language,
            template_id=template_id,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            limit=limit,
        )
    )

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository
from plugin_hub_api.schemas import JsonValue, Platform, StrictBaseModel
from plugin_hub_api.services.insights import generate_strategy_notes

router = APIRouter()


class StrategyNotesResponse(StrictBaseModel):
    items: list[dict[str, JsonValue]]


@router.get("/strategy-notes", response_model=StrategyNotesResponse)
def list_strategy_notes(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
) -> StrategyNotesResponse:
    units = repository.list_voc_units(platform=platform)
    return StrategyNotesResponse(items=generate_strategy_notes(units))

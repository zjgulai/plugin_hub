from __future__ import annotations

import secrets
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import Field
from sqlalchemy.orm import Session

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.schemas import (
    CollectionRun,
    CollectionRunCreate,
    JsonValue,
    Platform,
    RawSourceItem,
    StrictBaseModel,
)
from plugin_hub_api.services.collection_runs import map_raw_item_to_voc

router = APIRouter()


class CollectionRunRequest(StrictBaseModel):
    run: CollectionRunCreate
    raw_items: list[RawSourceItem] = Field(min_length=1)


class CollectionRunResponse(StrictBaseModel):
    collection_run_id: str
    raw_item_count: int
    voc_unit_count: int


class VocUnitsResponse(StrictBaseModel):
    items: list[dict[str, JsonValue]]


def get_session(request: Request) -> Generator[Session]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


def get_repository(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAlchemyRepository:
    return SqlAlchemyRepository(session)


@router.post(
    "/collection-runs",
    response_model=CollectionRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_collection_run(
    payload: CollectionRunRequest,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
) -> CollectionRunResponse:
    run = CollectionRun.model_validate(
        {
            **payload.run.model_dump(mode="json"),
            "collection_run_id": f"run_{secrets.token_hex(6)}",
            "created_at": datetime.now(tz=UTC),
        }
    )
    voc_units = [
        map_raw_item_to_voc(
            run=run,
            raw_item=raw_item,
        )
        for raw_item in payload.raw_items
    ]

    repository.save_collection(run=run, raw_items=payload.raw_items, voc_units=voc_units)

    return CollectionRunResponse(
        collection_run_id=run.collection_run_id,
        raw_item_count=len(payload.raw_items),
        voc_unit_count=len(voc_units),
    )


@router.get("/voc-units", response_model=VocUnitsResponse)
def list_voc_units(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
) -> VocUnitsResponse:
    items = [unit.model_dump(mode="json") for unit in repository.list_voc_units(platform=platform)]
    return VocUnitsResponse(items=items)

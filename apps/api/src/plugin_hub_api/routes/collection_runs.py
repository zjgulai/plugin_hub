from __future__ import annotations

import secrets
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    CollectionRun,
    CollectionRunCreate,
    JsonValue,
    Platform,
    RawSourceItem,
    SourceKind,
    StrictBaseModel,
)
from plugin_hub_api.services.etl import (
    map_amazon_review_to_voc,
    map_reddit_comment_to_voc,
    map_reddit_thread_to_voc,
)

router = APIRouter()


class CollectionRunRequest(StrictBaseModel):
    run: CollectionRunCreate
    raw_items: list[RawSourceItem]


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
        _map_raw_item(
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


def _map_raw_item(
    *,
    run: CollectionRun,
    raw_item: RawSourceItem,
) -> CanonicalVocUnit:
    source_url = str(run.model_dump(mode="json")["source_url"])

    if raw_item.source_kind == SourceKind.AMAZON_REVIEW:
        return map_amazon_review_to_voc(
            collection_run_id=run.collection_run_id,
            source_url=source_url,
            raw_review=raw_item.raw_payload,
            coverage_confidence=run.coverage_confidence,
        )
    if raw_item.source_kind == SourceKind.REDDIT_THREAD:
        return map_reddit_thread_to_voc(
            collection_run_id=run.collection_run_id,
            source_url=source_url,
            raw_thread=raw_item.raw_payload,
            coverage_confidence=run.coverage_confidence,
        )
    return map_reddit_comment_to_voc(
        collection_run_id=run.collection_run_id,
        source_url=source_url,
        thread_id=_reddit_comment_thread_id(raw_item.raw_payload),
        raw_comment=raw_item.raw_payload,
        coverage_confidence=run.coverage_confidence,
    )


def _reddit_comment_thread_id(raw_payload: dict[str, JsonValue]) -> str:
    link_id = raw_payload.get("link_id")
    if isinstance(link_id, str):
        return link_id

    thread_id = raw_payload.get("thread_id")
    if isinstance(thread_id, str):
        return thread_id

    return ""

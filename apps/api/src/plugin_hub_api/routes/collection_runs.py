from __future__ import annotations

import hashlib
import secrets
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from plugin_hub_api.payload_hashes import extension_payload_hash_matches
from plugin_hub_api.repositories import CollectionReplayState, SqlAlchemyRepository
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
    raw_items: list[RawSourceItem] = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_raw_item_set(self) -> CollectionRunRequest:
        source_objects: set[tuple[Platform, object, str]] = set()
        for item in self.raw_items:
            if item.platform != self.run.platform:
                raise ValueError("collection_run_platform_mismatch")
            identity = (item.platform, item.source_kind, item.source_object_id)
            if identity in source_objects:
                raise ValueError("duplicate_source_object_in_collection_run")
            source_objects.add(identity)
            if self.run.capture_method.startswith("extension_") and not (
                extension_payload_hash_matches(item.raw_payload, item.raw_payload_hash)
            ):
                raise ValueError("raw_payload_hash_mismatch")
        return self


class CollectionRunResponse(StrictBaseModel):
    collection_run_id: str
    raw_item_count: int
    voc_unit_count: int
    replayed: bool


class VocUnitsResponse(StrictBaseModel):
    items: list[dict[str, JsonValue]]
    total: int
    limit: int
    offset: int


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
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=16, max_length=128),
    ] = None,
) -> CollectionRunResponse:
    collection_run_id = _collection_run_id(idempotency_key)
    replay = repository.get_collection_replay_state(
        collection_run_id=collection_run_id,
        run=payload.run,
        raw_items=payload.raw_items,
    )
    if replay is not None:
        return _replay_response(collection_run_id, replay)

    run = CollectionRun.model_validate(
        {
            **payload.run.model_dump(mode="json"),
            "collection_run_id": collection_run_id,
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

    try:
        repository.save_collection(run=run, raw_items=payload.raw_items, voc_units=voc_units)
    except IntegrityError:
        replay = repository.get_collection_replay_state(
            collection_run_id=collection_run_id,
            run=payload.run,
            raw_items=payload.raw_items,
        )
        if replay is None:
            raise
        return _replay_response(collection_run_id, replay)

    return CollectionRunResponse(
        collection_run_id=run.collection_run_id,
        raw_item_count=len(payload.raw_items),
        voc_unit_count=len(voc_units),
        replayed=False,
    )


def _collection_run_id(idempotency_key: str | None) -> str:
    if idempotency_key is None:
        return f"run_{secrets.token_hex(6)}"
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
    return f"run_i_{digest}"


def _replay_response(
    collection_run_id: str,
    replay: CollectionReplayState,
) -> CollectionRunResponse:
    if not replay.matches_payload:
        raise HTTPException(status_code=409, detail="idempotency_key_payload_conflict")
    return CollectionRunResponse(
        collection_run_id=collection_run_id,
        raw_item_count=replay.raw_item_count,
        voc_unit_count=replay.voc_unit_count,
        replayed=True,
    )


@router.get("/voc-units", response_model=VocUnitsResponse)
def list_voc_units(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> VocUnitsResponse:
    items = [
        unit.model_dump(mode="json")
        for unit in repository.list_voc_units(
            platform=platform,
            limit=limit,
            offset=offset,
            newest_first=True,
        )
    ]
    return VocUnitsResponse(
        items=items,
        total=repository.count_voc_units(platform=platform),
        limit=limit,
        offset=offset,
    )

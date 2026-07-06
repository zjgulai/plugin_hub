from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AnyHttpUrl, field_validator

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository
from plugin_hub_api.schemas import (
    CollectionRun,
    JsonValue,
    Platform,
    StrictBaseModel,
    ensure_json_object,
)
from plugin_hub_api.services.collection_runs import map_raw_item_to_voc
from plugin_hub_api.services.instagram_capture import capture_instagram_media_comments_payload

router = APIRouter()


class InstagramMediaCommentsCaptureRequest(StrictBaseModel):
    source_url: AnyHttpUrl
    payload: dict[str, JsonValue]

    @field_validator("payload", mode="before")
    @classmethod
    def validate_payload(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class InstagramMediaCommentsCaptureResponse(StrictBaseModel):
    collection_run_id: str
    raw_item_count: int
    voc_unit_count: int
    comment_count: int
    stop_reason: str | None
    coverage_confidence: float


@router.post(
    "/instagram-media-comment-captures",
    response_model=InstagramMediaCommentsCaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_instagram_media_comment_capture(
    payload: InstagramMediaCommentsCaptureRequest,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
) -> InstagramMediaCommentsCaptureResponse:
    source_url = str(payload.model_dump(mode="json")["source_url"])
    captured_at = datetime.now(tz=UTC)
    capture = capture_instagram_media_comments_payload(
        payload=payload.payload,
        source_url=source_url,
        captured_at=captured_at,
    )

    if not capture.raw_items:
        raise HTTPException(
            status_code=422,
            detail=capture.stop_reason or "instagram_capture_no_raw_items",
        )

    run = CollectionRun.model_validate(
        {
            "collection_run_id": f"run_{secrets.token_hex(6)}",
            "platform": Platform.INSTAGRAM,
            "source_url": source_url,
            "capture_method": "server_instagram_fixture_payload",
            "coverage_scope": {
                "collector_app": "web_instagram_fixture_payload",
                "page_kind": "instagram_media_comments",
                "comment_count": capture.comment_count,
                "raw_item_count": len(capture.raw_items),
            },
            "stop_reason": capture.stop_reason,
            "coverage_confidence": capture.coverage_confidence,
            "created_at": datetime.now(tz=UTC),
        }
    )
    voc_units = [map_raw_item_to_voc(run=run, raw_item=raw_item) for raw_item in capture.raw_items]
    repository.save_collection(run=run, raw_items=capture.raw_items, voc_units=voc_units)

    return InstagramMediaCommentsCaptureResponse(
        collection_run_id=run.collection_run_id,
        raw_item_count=len(capture.raw_items),
        voc_unit_count=len(voc_units),
        comment_count=capture.comment_count,
        stop_reason=capture.stop_reason,
        coverage_confidence=capture.coverage_confidence,
    )

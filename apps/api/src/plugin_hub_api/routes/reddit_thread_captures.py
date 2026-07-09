from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AnyHttpUrl

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository
from plugin_hub_api.routes.collection_tasks import get_reddit_json_fetcher
from plugin_hub_api.schemas import CollectionRun, Platform, StrictBaseModel
from plugin_hub_api.services.collection_runs import map_raw_item_to_voc
from plugin_hub_api.services.collection_task_worker import stable_error
from plugin_hub_api.services.reddit_capture import (
    RedditOAuthConfigurationError,
    RedditOAuthTokenError,
    RedditUpstreamAccessError,
    capture_reddit_thread_json,
)

router = APIRouter()


class RedditThreadCaptureRequest(StrictBaseModel):
    source_url: AnyHttpUrl


class RedditThreadCaptureResponse(StrictBaseModel):
    collection_run_id: str
    raw_item_count: int
    voc_unit_count: int
    json_url: str
    more_node_count: int
    stop_reason: str | None
    coverage_confidence: float


@router.post(
    "/reddit-thread-captures",
    response_model=RedditThreadCaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reddit_thread_capture(
    payload: RedditThreadCaptureRequest,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    reddit_json_fetcher: Annotated[Callable[[str], object], Depends(get_reddit_json_fetcher)],
) -> RedditThreadCaptureResponse:
    source_url = str(payload.model_dump(mode="json")["source_url"])
    captured_at = datetime.now(tz=UTC)

    try:
        capture = capture_reddit_thread_json(
            source_url=source_url,
            captured_at=captured_at,
            fetcher=reddit_json_fetcher,
        )
    except (
        RedditOAuthConfigurationError,
        RedditOAuthTokenError,
        RedditUpstreamAccessError,
        ValueError,
        OSError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_reddit_capture_error_detail(error),
        ) from error

    if not capture.raw_items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=capture.stop_reason or "reddit_capture_no_raw_items",
        )

    stop_reason = _effective_stop_reason(
        stop_reason=capture.stop_reason,
        more_node_count=capture.more_node_count,
    )
    run = CollectionRun.model_validate(
        {
            "collection_run_id": f"run_{secrets.token_hex(6)}",
            "platform": Platform.REDDIT,
            "source_url": source_url,
            "capture_method": "server_reddit_json_url_input",
            "coverage_scope": {
                "collector_app": "web_reddit_url_input",
                "page_kind": "reddit_thread",
                "json_url": capture.json_url,
                "more_node_count": capture.more_node_count,
                "raw_item_count": len(capture.raw_items),
            },
            "stop_reason": stop_reason,
            "coverage_confidence": capture.coverage_confidence,
            "created_at": datetime.now(tz=UTC),
        }
    )
    voc_units = [map_raw_item_to_voc(run=run, raw_item=raw_item) for raw_item in capture.raw_items]
    repository.save_collection(run=run, raw_items=capture.raw_items, voc_units=voc_units)

    return RedditThreadCaptureResponse(
        collection_run_id=run.collection_run_id,
        raw_item_count=len(capture.raw_items),
        voc_unit_count=len(voc_units),
        json_url=capture.json_url,
        more_node_count=capture.more_node_count,
        stop_reason=stop_reason,
        coverage_confidence=capture.coverage_confidence,
    )


def _effective_stop_reason(*, stop_reason: str | None, more_node_count: int) -> str | None:
    return stop_reason or ("more_nodes_not_expanded" if more_node_count > 0 else None)


def _reddit_capture_error_detail(error: Exception) -> str:
    message = stable_error(error)
    if isinstance(error, RedditUpstreamAccessError) and message in {
        "reddit_upstream_http_401",
        "reddit_upstream_http_403",
    }:
        return "reddit_capture_requires_authorized_access"
    if isinstance(error, RedditOAuthConfigurationError):
        return "reddit_oauth_configuration_error"
    if isinstance(error, RedditOAuthTokenError):
        return "reddit_oauth_token_error"
    return "reddit_capture_failed"

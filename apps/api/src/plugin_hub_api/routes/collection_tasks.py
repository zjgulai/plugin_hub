from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from plugin_hub_api.repositories import CollectionTaskClaimLostError, SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository
from plugin_hub_api.schemas import (
    CollectionTask,
    CollectionTaskCreate,
    CollectionTaskStatus,
    JsonValue,
    Platform,
    StrictBaseModel,
)
from plugin_hub_api.services.collection_task_worker import (
    CollectionTaskNotFoundError,
    CollectionTaskNotRunnableError,
    CollectionTaskRunResult,
    CollectionTaskWorkerConfig,
    PendingCollectionTaskNotFoundError,
    run_collection_task,
    run_next_collection_task,
)
from plugin_hub_api.services.instagram_graph_capture import InstagramGraphCommentsFetcher
from plugin_hub_api.services.reddit_capture import default_reddit_json_fetcher

router = APIRouter()
OPEN_COLLECTION_TASK_STATUSES = (
    CollectionTaskStatus.PENDING,
    CollectionTaskStatus.RUNNING,
    CollectionTaskStatus.RETRY_SCHEDULED,
)


class CollectionTaskRequest(StrictBaseModel):
    task: CollectionTaskCreate


class CollectionTaskResponse(StrictBaseModel):
    collection_task_id: str
    platform: Platform
    source_url: str
    requested_capture_method: str
    trigger_reason: str
    status: CollectionTaskStatus
    context: dict[str, JsonValue]
    created_at: datetime
    updated_at: datetime


class CollectionTasksResponse(StrictBaseModel):
    items: list[CollectionTaskResponse]
    total: int
    open_total: int
    open_totals: dict[Platform, int]
    limit: int
    offset: int


class CollectionTaskRunResponse(StrictBaseModel):
    task: CollectionTaskResponse
    status: CollectionTaskStatus
    collection_run_id: str | None
    raw_item_count: int
    voc_unit_count: int


@router.post(
    "/collection-tasks",
    response_model=CollectionTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_collection_task(
    payload: CollectionTaskRequest,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
) -> CollectionTaskResponse:
    now = datetime.now(tz=UTC)
    task = CollectionTask.model_validate(
        {
            **payload.task.model_dump(mode="json"),
            "collection_task_id": f"task_{secrets.token_hex(6)}",
            "status": CollectionTaskStatus.PENDING,
            "created_at": now,
            "updated_at": now,
        }
    )
    repository.save_collection_task(task)
    return _task_response(task)


@router.get("/collection-tasks", response_model=CollectionTasksResponse)
def list_collection_tasks(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> CollectionTasksResponse:
    repository.begin_read_snapshot()
    try:
        open_totals = {
            current_platform: repository.count_collection_tasks(
                platform=current_platform,
                statuses=OPEN_COLLECTION_TASK_STATUSES,
            )
            for current_platform in Platform
        }
        return CollectionTasksResponse(
            items=[
                _task_response(task)
                for task in repository.list_collection_tasks(
                    platform=platform,
                    limit=limit,
                    offset=offset,
                )
            ],
            total=repository.count_collection_tasks(platform=platform),
            open_total=(
                open_totals[platform]
                if platform is not None
                else sum(open_totals.values())
            ),
            open_totals=open_totals,
            limit=limit,
            offset=offset,
        )
    finally:
        repository.end_read_snapshot()


@router.post(
    "/collection-tasks/run-next",
    response_model=CollectionTaskRunResponse,
)
def run_next_collection_task_endpoint(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    reddit_json_fetcher: Annotated[Callable[[str], object], Depends(get_reddit_json_fetcher)],
    instagram_graph_comments_fetcher: Annotated[
        InstagramGraphCommentsFetcher | None,
        Depends(get_instagram_graph_comments_fetcher),
    ],
    worker_config: Annotated[
        CollectionTaskWorkerConfig, Depends(get_collection_task_worker_config)
    ],
) -> CollectionTaskRunResponse:
    try:
        result = run_next_collection_task(
            repository=repository,
            reddit_json_fetcher=reddit_json_fetcher,
            instagram_graph_comments_fetcher=instagram_graph_comments_fetcher,
            config=worker_config,
        )
    except PendingCollectionTaskNotFoundError:
        raise HTTPException(status_code=404, detail="pending_collection_task_not_found") from None
    except CollectionTaskClaimLostError:
        raise HTTPException(status_code=409, detail="collection_task_claim_lost") from None

    return _task_run_response(result)


@router.post(
    "/collection-tasks/{collection_task_id}/run",
    response_model=CollectionTaskRunResponse,
)
def run_collection_task_endpoint(
    collection_task_id: str,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    reddit_json_fetcher: Annotated[Callable[[str], object], Depends(get_reddit_json_fetcher)],
    instagram_graph_comments_fetcher: Annotated[
        InstagramGraphCommentsFetcher | None,
        Depends(get_instagram_graph_comments_fetcher),
    ],
    worker_config: Annotated[
        CollectionTaskWorkerConfig, Depends(get_collection_task_worker_config)
    ],
) -> CollectionTaskRunResponse:
    try:
        result = run_collection_task(
            collection_task_id=collection_task_id,
            repository=repository,
            reddit_json_fetcher=reddit_json_fetcher,
            instagram_graph_comments_fetcher=instagram_graph_comments_fetcher,
            config=worker_config,
        )
    except CollectionTaskNotFoundError:
        raise HTTPException(status_code=404, detail="collection_task_not_found") from None
    except CollectionTaskNotRunnableError:
        raise HTTPException(status_code=409, detail="collection_task_not_runnable") from None
    except CollectionTaskClaimLostError:
        raise HTTPException(status_code=409, detail="collection_task_claim_lost") from None

    return _task_run_response(result)


def get_reddit_json_fetcher(request: Request) -> Callable[[str], object]:
    fetcher = getattr(request.app.state, "reddit_json_fetcher", None)
    return fetcher if callable(fetcher) else default_reddit_json_fetcher


def get_instagram_graph_comments_fetcher(request: Request) -> InstagramGraphCommentsFetcher | None:
    fetcher = getattr(request.app.state, "instagram_graph_comments_fetcher", None)
    return fetcher if callable(fetcher) else None


def get_collection_task_worker_config(request: Request) -> CollectionTaskWorkerConfig:
    config = getattr(request.app.state, "collection_task_worker_config", None)
    if isinstance(config, CollectionTaskWorkerConfig):
        return config
    return CollectionTaskWorkerConfig()


def _task_response(task: CollectionTask) -> CollectionTaskResponse:
    public_context = {
        key: value for key, value in task.context.items() if key != "claim_token"
    }
    return CollectionTaskResponse(
        collection_task_id=task.collection_task_id,
        platform=task.platform,
        source_url=str(task.model_dump(mode="json")["source_url"]),
        requested_capture_method=task.requested_capture_method,
        trigger_reason=task.trigger_reason,
        status=task.status,
        context=public_context,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _task_run_response(result: CollectionTaskRunResult) -> CollectionTaskRunResponse:
    return CollectionTaskRunResponse(
        task=_task_response(result.task),
        status=result.task.status,
        collection_run_id=result.collection_run_id,
        raw_item_count=result.raw_item_count,
        voc_unit_count=result.voc_unit_count,
    )

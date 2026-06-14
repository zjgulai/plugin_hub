from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.schemas import (
    CollectionRun,
    CollectionTask,
    CollectionTaskStatus,
    JsonValue,
    Platform,
)
from plugin_hub_api.services.collection_runs import map_raw_item_to_voc
from plugin_hub_api.services.reddit_capture import RedditJsonFetcher, capture_reddit_thread_json


class CollectionTaskNotFoundError(Exception):
    pass


class PendingCollectionTaskNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class CollectionTaskWorkerConfig:
    max_attempts: int = 3
    retry_delay_seconds: int = 300
    worker_id: str = "local-worker"
    claim_ttl_seconds: int = 900


@dataclass(frozen=True)
class CollectionTaskRunResult:
    task: CollectionTask
    collection_run_id: str | None
    raw_item_count: int
    voc_unit_count: int


@dataclass(frozen=True)
class CollectionTaskFailure:
    code: str
    message: str
    retryable: bool


def run_collection_task(
    *,
    collection_task_id: str,
    repository: SqlAlchemyRepository,
    reddit_json_fetcher: RedditJsonFetcher | None = None,
    config: CollectionTaskWorkerConfig | None = None,
) -> CollectionTaskRunResult:
    resolved_config = config if config is not None else CollectionTaskWorkerConfig()
    task = repository.get_collection_task(collection_task_id)
    if task is None:
        raise CollectionTaskNotFoundError(collection_task_id)

    started_at = datetime.now(tz=UTC)
    attempt_count = _next_attempt_count(task)
    running_task = _task_with_context(
        task,
        status=CollectionTaskStatus.RUNNING,
        updated_at=started_at,
        context_updates={
            "attempt_count": attempt_count,
            "max_attempts": resolved_config.max_attempts,
            "worker_id": resolved_config.worker_id,
            "worker_started_at": started_at.isoformat(),
            "last_attempt_started_at": started_at.isoformat(),
            "next_run_at": None,
        },
    )
    repository.update_collection_task(running_task)

    try:
        if running_task.platform != Platform.REDDIT:
            raise ValueError("collection_task_platform_unsupported")
        if running_task.requested_capture_method != "server_reddit_json_proxy":
            raise ValueError("collection_task_capture_method_unsupported")

        capture = capture_reddit_thread_json(
            source_url=str(running_task.model_dump(mode="json")["source_url"]),
            captured_at=started_at,
            fetcher=reddit_json_fetcher,
        )
        if not capture.raw_items:
            return _mark_failed_or_retry(
                repository=repository,
                task=running_task,
                failure=CollectionTaskFailure(
                    code="reddit_capture_no_raw_items",
                    message="Reddit JSON returned no raw VOC items.",
                    retryable=False,
                ),
                config=resolved_config,
                attempt_count=attempt_count,
                context_updates={
                    "json_url": capture.json_url,
                    "stop_reason": capture.stop_reason or "unknown",
                    "raw_item_count": 0,
                },
            )

        run = CollectionRun.model_validate(
            {
                "collection_run_id": f"run_{secrets.token_hex(6)}",
                "platform": Platform.REDDIT,
                "source_url": str(running_task.model_dump(mode="json")["source_url"]),
                "capture_method": "server_reddit_json_proxy",
                "coverage_scope": {
                    "page_kind": "reddit_thread",
                    "collection_task_id": running_task.collection_task_id,
                    "json_url": capture.json_url,
                    "more_node_count": capture.more_node_count,
                    "raw_item_count": len(capture.raw_items),
                },
                "stop_reason": capture.stop_reason,
                "coverage_confidence": capture.coverage_confidence,
                "created_at": datetime.now(tz=UTC),
            }
        )
        voc_units = [
            map_raw_item_to_voc(run=run, raw_item=raw_item)
            for raw_item in capture.raw_items
        ]
        completed_at = datetime.now(tz=UTC)
        completed_task = _task_with_context(
            running_task,
            status=CollectionTaskStatus.COMPLETED,
            updated_at=completed_at,
            context_updates={
                "collection_run_id": run.collection_run_id,
                "json_url": capture.json_url,
                "raw_item_count": len(capture.raw_items),
                "voc_unit_count": len(voc_units),
                "worker_completed_at": completed_at.isoformat(),
                "last_error_code": None,
                "last_error_message": None,
                "retryable": False,
                "next_run_at": None,
                "claimed_by": None,
                "claimed_at": None,
                "claim_expires_at": None,
            },
        )
        repository.save_collection_and_update_task(
            run=run,
            raw_items=capture.raw_items,
            voc_units=voc_units,
            task=completed_task,
        )
        return CollectionTaskRunResult(
            task=completed_task,
            collection_run_id=run.collection_run_id,
            raw_item_count=len(capture.raw_items),
            voc_unit_count=len(voc_units),
        )
    except Exception as error:
        return _mark_failed_or_retry(
            repository=repository,
            task=running_task,
            failure=_classify_failure(error),
            config=resolved_config,
            attempt_count=attempt_count,
            context_updates={},
        )


def run_next_collection_task(
    *,
    repository: SqlAlchemyRepository,
    reddit_json_fetcher: RedditJsonFetcher | None = None,
    config: CollectionTaskWorkerConfig | None = None,
) -> CollectionTaskRunResult:
    resolved_config = config if config is not None else CollectionTaskWorkerConfig()
    task = repository.claim_next_runnable_collection_task(
        worker_id=resolved_config.worker_id,
        claim_ttl_seconds=resolved_config.claim_ttl_seconds,
        now=datetime.now(tz=UTC),
    )
    if task is None:
        raise PendingCollectionTaskNotFoundError

    return run_collection_task(
        collection_task_id=task.collection_task_id,
        repository=repository,
        reddit_json_fetcher=reddit_json_fetcher,
        config=resolved_config,
    )


def _mark_failed_or_retry(
    *,
    repository: SqlAlchemyRepository,
    task: CollectionTask,
    failure: CollectionTaskFailure,
    config: CollectionTaskWorkerConfig,
    attempt_count: int,
    context_updates: dict[str, JsonValue],
) -> CollectionTaskRunResult:
    failed_at = datetime.now(tz=UTC)
    should_retry = failure.retryable and attempt_count < config.max_attempts
    next_run_at = (
        failed_at + timedelta(seconds=config.retry_delay_seconds)
        if should_retry
        else None
    )
    failed_task = _task_with_context(
        task,
        status=(
            CollectionTaskStatus.RETRY_SCHEDULED
            if should_retry
            else CollectionTaskStatus.FAILED
        ),
        updated_at=failed_at,
        context_updates={
            **context_updates,
            "last_error_code": failure.code,
            "last_error_message": failure.message,
            "retryable": failure.retryable,
            "retry_scheduled": should_retry,
            "attempt_count": attempt_count,
            "max_attempts": config.max_attempts,
            "next_run_at": next_run_at.isoformat() if next_run_at is not None else None,
            "last_failed_at": failed_at.isoformat(),
            "error": failure.code,
            "worker_failed_at": failed_at.isoformat(),
            "claimed_by": None,
            "claimed_at": None,
            "claim_expires_at": None,
        },
    )
    repository.update_collection_task(failed_task)
    return CollectionTaskRunResult(
        task=failed_task,
        collection_run_id=None,
        raw_item_count=0,
        voc_unit_count=0,
    )


def _next_attempt_count(task: CollectionTask) -> int:
    attempt_count = task.context.get("attempt_count")
    if isinstance(attempt_count, int) and attempt_count >= 0:
        return attempt_count + 1
    return 1


def _classify_failure(error: Exception) -> CollectionTaskFailure:
    message = stable_error(error)
    if message in {
        "collection_task_platform_unsupported",
        "collection_task_capture_method_unsupported",
    }:
        return CollectionTaskFailure(
            code=message,
            message=message,
            retryable=False,
        )
    return CollectionTaskFailure(
        code="collection_task_worker_error",
        message=message,
        retryable=True,
    )


def _task_with_context(
    task: CollectionTask,
    *,
    status: CollectionTaskStatus,
    updated_at: datetime,
    context_updates: dict[str, JsonValue],
) -> CollectionTask:
    return task.model_copy(
        update={
            "status": status,
            "updated_at": updated_at,
            "context": {
                **task.context,
                **context_updates,
            },
        }
    )


def stable_error(error: Exception) -> str:
    return str(error) or error.__class__.__name__

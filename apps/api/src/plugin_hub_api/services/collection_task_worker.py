from __future__ import annotations

import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from plugin_hub_api.repositories import CollectionTaskClaimLostError, SqlAlchemyRepository
from plugin_hub_api.schemas import (
    CollectionRun,
    CollectionTask,
    CollectionTaskStatus,
    JsonValue,
    Platform,
    RawSourceItem,
    ensure_json_object,
)
from plugin_hub_api.services.collection_runs import map_raw_item_to_voc
from plugin_hub_api.services.instagram_capture import capture_instagram_media_comments_payload
from plugin_hub_api.services.instagram_graph_authorization import (
    validate_instagram_graph_live_read_context,
)
from plugin_hub_api.services.instagram_graph_capture import (
    InstagramGraphAccessError,
    InstagramGraphCommentsFetcher,
    InstagramGraphCommentsFetcherClient,
    InstagramGraphConfigurationError,
    capture_instagram_media_comments_graph,
)
from plugin_hub_api.services.reddit_capture import (
    RedditJsonFetcher,
    RedditOAuthConfigurationError,
    RedditOAuthTokenError,
    RedditUpstreamAccessError,
    capture_reddit_thread_json,
)

type CollectionTaskHandlerKey = tuple[Platform, str]
type CollectionTaskHandler = Callable[[CollectionTask, datetime], CollectionTaskCapture]


class CollectionTaskNotFoundError(Exception):
    pass


class CollectionTaskNotRunnableError(Exception):
    pass


class PendingCollectionTaskNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class CollectionTaskWorkerConfig:
    max_attempts: int = 3
    retry_delay_seconds: int = 300
    worker_id: str = "local-worker"
    claim_ttl_seconds: int = 900
    instagram_graph_live_read_enabled: bool = False
    amazon_page_limit: int = 3
    reddit_max_comment_depth: int = 8
    instagram_fixture_mode_enabled: bool = True
    instagram_graph_api_version: str = "v25.0"
    instagram_graph_comment_limit: int = 50


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


@dataclass(frozen=True)
class CollectionTaskCapture:
    platform: Platform
    capture_method: str
    coverage_scope: dict[str, JsonValue]
    stop_reason: str | None
    coverage_confidence: float
    raw_items: list[RawSourceItem]
    empty_error_code: str
    empty_error_message: str
    context_updates: dict[str, JsonValue]
    empty_context_updates: dict[str, JsonValue]


@dataclass(frozen=True)
class PlatformTaskRuntimeSettings:
    enabled: bool
    source: str
    config: dict[str, JsonValue]


def run_collection_task(
    *,
    collection_task_id: str,
    repository: SqlAlchemyRepository,
    reddit_json_fetcher: RedditJsonFetcher | None = None,
    instagram_graph_comments_fetcher: InstagramGraphCommentsFetcher | None = None,
    capture_handlers: Mapping[CollectionTaskHandlerKey, CollectionTaskHandler] | None = None,
    config: CollectionTaskWorkerConfig | None = None,
    _claimed_task: CollectionTask | None = None,
) -> CollectionTaskRunResult:
    resolved_config = config if config is not None else CollectionTaskWorkerConfig()
    resolved_handlers = (
        capture_handlers
        if capture_handlers is not None
        else build_collection_task_capture_handlers(
            reddit_json_fetcher=reddit_json_fetcher,
            instagram_graph_comments_fetcher=instagram_graph_comments_fetcher,
            instagram_graph_live_read_enabled=(resolved_config.instagram_graph_live_read_enabled),
        )
    )
    task = _claimed_task
    if task is None:
        task = repository.claim_collection_task(
            collection_task_id=collection_task_id,
            worker_id=resolved_config.worker_id,
            claim_ttl_seconds=resolved_config.claim_ttl_seconds,
            now=datetime.now(tz=UTC),
        )
    if task is None:
        if repository.get_collection_task(collection_task_id) is None:
            raise CollectionTaskNotFoundError(collection_task_id)
        raise CollectionTaskNotRunnableError(collection_task_id)
    claim_token = _collection_task_claim_token(task)

    started_at = datetime.now(tz=UTC)
    attempt_count = _next_attempt_count(task)
    platform_runtime_settings = _platform_task_runtime_settings(
        repository=repository,
        platform=task.platform,
        config=resolved_config,
    )
    running_task = _task_with_context(
        task,
        status=CollectionTaskStatus.RUNNING,
        updated_at=started_at,
        context_updates={
            "attempt_count": attempt_count,
            "max_attempts": resolved_config.max_attempts,
            "platform_setting_source": platform_runtime_settings.source,
            "platform_enabled_at_run": platform_runtime_settings.enabled,
            "platform_config_applied": platform_runtime_settings.config,
            "worker_id": resolved_config.worker_id,
            "worker_started_at": started_at.isoformat(),
            "last_attempt_started_at": started_at.isoformat(),
            "next_run_at": None,
        },
    )
    repository.update_collection_task(
        running_task,
        expected_claim_token=claim_token,
    )

    if not platform_runtime_settings.enabled:
        return _mark_failed_or_retry(
            repository=repository,
            task=running_task,
            failure=CollectionTaskFailure(
                code="platform_disabled_by_settings",
                message="platform_disabled_by_settings",
                retryable=False,
            ),
            config=resolved_config,
            attempt_count=attempt_count,
            context_updates={},
            claim_token=claim_token,
        )

    try:
        capture = _run_capture_handler(
            task=running_task,
            captured_at=started_at,
            capture_handlers=resolved_handlers,
        )
        if not capture.raw_items:
            return _mark_failed_or_retry(
                repository=repository,
                task=running_task,
                failure=CollectionTaskFailure(
                    code=capture.empty_error_code,
                    message=capture.empty_error_message,
                    retryable=False,
                ),
                config=resolved_config,
                attempt_count=attempt_count,
                context_updates={
                    **capture.empty_context_updates,
                    "stop_reason": capture.stop_reason or "unknown",
                    "raw_item_count": 0,
                },
                claim_token=claim_token,
            )

        run = CollectionRun.model_validate(
            {
                "collection_run_id": f"run_{secrets.token_hex(6)}",
                "platform": capture.platform,
                "source_url": str(running_task.model_dump(mode="json")["source_url"]),
                "capture_method": capture.capture_method,
                "coverage_scope": {
                    **capture.coverage_scope,
                    "collection_task_id": running_task.collection_task_id,
                    "raw_item_count": len(capture.raw_items),
                },
                "stop_reason": capture.stop_reason,
                "coverage_confidence": capture.coverage_confidence,
                "created_at": datetime.now(tz=UTC),
            }
        )
        voc_units = [
            map_raw_item_to_voc(run=run, raw_item=raw_item) for raw_item in capture.raw_items
        ]
        completed_at = datetime.now(tz=UTC)
        completed_task = _task_with_context(
            running_task,
            status=CollectionTaskStatus.COMPLETED,
            updated_at=completed_at,
            context_updates={
                "collection_run_id": run.collection_run_id,
                **capture.context_updates,
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
                "claim_token": None,
            },
        )
        repository.save_collection_and_update_task(
            run=run,
            raw_items=capture.raw_items,
            voc_units=voc_units,
            task=completed_task,
            expected_claim_token=claim_token,
        )
        return CollectionTaskRunResult(
            task=completed_task,
            collection_run_id=run.collection_run_id,
            raw_item_count=len(capture.raw_items),
            voc_unit_count=len(voc_units),
        )
    except CollectionTaskClaimLostError:
        raise
    except Exception as error:
        return _mark_failed_or_retry(
            repository=repository,
            task=running_task,
            failure=_classify_failure(error),
            config=resolved_config,
            attempt_count=attempt_count,
            context_updates={},
            claim_token=claim_token,
        )


def run_next_collection_task(
    *,
    repository: SqlAlchemyRepository,
    reddit_json_fetcher: RedditJsonFetcher | None = None,
    instagram_graph_comments_fetcher: InstagramGraphCommentsFetcher | None = None,
    capture_handlers: Mapping[CollectionTaskHandlerKey, CollectionTaskHandler] | None = None,
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
        instagram_graph_comments_fetcher=instagram_graph_comments_fetcher,
        capture_handlers=capture_handlers,
        config=resolved_config,
        _claimed_task=task,
    )


def build_collection_task_capture_handlers(
    *,
    reddit_json_fetcher: RedditJsonFetcher | None = None,
    instagram_graph_comments_fetcher: InstagramGraphCommentsFetcher | None = None,
    instagram_graph_live_read_enabled: bool = False,
) -> dict[CollectionTaskHandlerKey, CollectionTaskHandler]:
    return {
        (
            Platform.REDDIT,
            "server_reddit_json_proxy",
        ): lambda task, captured_at: _capture_reddit_task(
            task=task,
            captured_at=captured_at,
            reddit_json_fetcher=reddit_json_fetcher,
        ),
        (
            Platform.INSTAGRAM,
            "server_instagram_fixture_payload",
        ): _capture_instagram_fixture_task,
        (
            Platform.INSTAGRAM,
            "server_instagram_graph_comments",
        ): lambda task, captured_at: _capture_instagram_graph_comments_task(
            task=task,
            captured_at=captured_at,
            instagram_graph_comments_fetcher=instagram_graph_comments_fetcher,
            instagram_graph_live_read_enabled=instagram_graph_live_read_enabled,
        ),
    }


def _run_capture_handler(
    *,
    task: CollectionTask,
    captured_at: datetime,
    capture_handlers: Mapping[CollectionTaskHandlerKey, CollectionTaskHandler],
) -> CollectionTaskCapture:
    handler = capture_handlers.get((task.platform, task.requested_capture_method))
    if handler is None:
        raise ValueError("collection_task_capture_method_unsupported")
    return handler(task, captured_at)


def _capture_reddit_task(
    *,
    task: CollectionTask,
    captured_at: datetime,
    reddit_json_fetcher: RedditJsonFetcher | None,
) -> CollectionTaskCapture:
    platform_config = _context_object(task.context.get("platform_config_applied"))
    if platform_config.get("json_proxy_enabled") is False:
        raise ValueError("reddit_json_proxy_disabled_by_settings")
    max_comment_depth = _context_int(
        platform_config.get("max_comment_depth"),
        fallback=8,
        minimum=0,
        maximum=10,
    )
    capture = capture_reddit_thread_json(
        source_url=str(task.model_dump(mode="json")["source_url"]),
        captured_at=captured_at,
        fetcher=reddit_json_fetcher,
        max_comment_depth=max_comment_depth,
    )
    return CollectionTaskCapture(
        platform=Platform.REDDIT,
        capture_method="server_reddit_json_proxy",
        coverage_scope={
            "page_kind": "reddit_thread",
            "json_url": capture.json_url,
            "more_node_count": capture.more_node_count,
            "max_comment_depth": max_comment_depth,
        },
        stop_reason=capture.stop_reason,
        coverage_confidence=capture.coverage_confidence,
        raw_items=capture.raw_items,
        empty_error_code="reddit_capture_no_raw_items",
        empty_error_message="Reddit JSON returned no raw VOC items.",
        context_updates={
            "json_url": capture.json_url,
            "more_node_count": capture.more_node_count,
            "max_comment_depth": max_comment_depth,
        },
        empty_context_updates={
            "json_url": capture.json_url,
            "more_node_count": capture.more_node_count,
            "max_comment_depth": max_comment_depth,
        },
    )


def _capture_instagram_fixture_task(
    task: CollectionTask,
    captured_at: datetime,
) -> CollectionTaskCapture:
    platform_config = _context_object(task.context.get("platform_config_applied"))
    if platform_config.get("fixture_mode_enabled") is False:
        raise ValueError("instagram_fixture_mode_disabled_by_settings")
    fixture_payload = task.context.get("fixture_payload")
    if not isinstance(fixture_payload, dict):
        raise ValueError("instagram_fixture_payload_required")
    checked_payload = ensure_json_object(fixture_payload)
    comment_limit = _context_int(
        platform_config.get("comment_limit"),
        fallback=50,
        minimum=1,
        maximum=100,
    )
    capture = capture_instagram_media_comments_payload(
        payload=_limit_instagram_comment_payload(checked_payload, comment_limit),
        source_url=str(task.model_dump(mode="json")["source_url"]),
        captured_at=captured_at,
    )
    return CollectionTaskCapture(
        platform=Platform.INSTAGRAM,
        capture_method="server_instagram_fixture_payload",
        coverage_scope={
            "collector_app": "server_instagram_fixture_payload",
            "page_kind": "instagram_media_comments",
            "comment_count": capture.comment_count,
            "comment_limit": comment_limit,
        },
        stop_reason=capture.stop_reason,
        coverage_confidence=capture.coverage_confidence,
        raw_items=capture.raw_items,
        empty_error_code="instagram_capture_no_raw_items",
        empty_error_message="Instagram fixture payload returned no raw VOC items.",
        context_updates={
            "comment_count": capture.comment_count,
            "comment_limit": comment_limit,
        },
        empty_context_updates={
            "comment_count": capture.comment_count,
            "comment_limit": comment_limit,
        },
    )


def _capture_instagram_graph_comments_task(
    *,
    task: CollectionTask,
    captured_at: datetime,
    instagram_graph_comments_fetcher: InstagramGraphCommentsFetcher | None,
    instagram_graph_live_read_enabled: bool,
) -> CollectionTaskCapture:
    if instagram_graph_comments_fetcher is None:
        raise InstagramGraphConfigurationError("instagram_graph_access_token_required")
    if not instagram_graph_live_read_enabled:
        raise InstagramGraphConfigurationError("instagram_graph_live_read_not_enabled")
    authorization_check = validate_instagram_graph_live_read_context(task.context)
    if authorization_check.blocking_code is not None:
        raise InstagramGraphConfigurationError(authorization_check.blocking_code)
    media_id = str(task.context["media_id"])
    platform_config = _context_object(task.context.get("platform_config_applied"))
    graph_api_version = _context_string(
        platform_config.get("graph_api_version"),
        fallback="v25.0",
    )
    comment_limit = _context_int(
        platform_config.get("comment_limit"),
        fallback=50,
        minimum=1,
        maximum=100,
    )

    capture_result = capture_instagram_media_comments_graph(
        media_id=media_id,
        source_url=str(task.model_dump(mode="json")["source_url"]),
        captured_at=captured_at,
        fetcher=_configured_instagram_graph_fetcher(
            instagram_graph_comments_fetcher,
            graph_api_version=graph_api_version,
            comment_limit=comment_limit,
        ),
    )
    capture = capture_result.capture
    coverage_scope: dict[str, JsonValue] = {
        "collector_app": "server_instagram_graph_comments",
        "page_kind": "instagram_media_comments",
        "media_id": capture_result.media_id,
        "comment_count": capture.comment_count,
        "graph_api_version": graph_api_version,
        "comment_limit": comment_limit,
    }
    context_updates: dict[str, JsonValue] = {
        "media_id": capture_result.media_id,
        "comment_count": capture.comment_count,
        "graph_api_version": graph_api_version,
        "comment_limit": comment_limit,
    }
    if capture_result.graph_url is not None:
        coverage_scope["graph_url"] = capture_result.graph_url
        context_updates["graph_url"] = capture_result.graph_url

    return CollectionTaskCapture(
        platform=Platform.INSTAGRAM,
        capture_method="server_instagram_graph_comments",
        coverage_scope=coverage_scope,
        stop_reason=capture.stop_reason,
        coverage_confidence=capture.coverage_confidence,
        raw_items=capture.raw_items,
        empty_error_code="instagram_capture_no_raw_items",
        empty_error_message="Instagram Graph returned no raw VOC items.",
        context_updates=context_updates,
        empty_context_updates=context_updates,
    )


def _mark_failed_or_retry(
    *,
    repository: SqlAlchemyRepository,
    task: CollectionTask,
    failure: CollectionTaskFailure,
    config: CollectionTaskWorkerConfig,
    attempt_count: int,
    context_updates: dict[str, JsonValue],
    claim_token: str,
) -> CollectionTaskRunResult:
    failed_at = datetime.now(tz=UTC)
    should_retry = failure.retryable and attempt_count < config.max_attempts
    next_run_at = (
        failed_at + timedelta(seconds=config.retry_delay_seconds) if should_retry else None
    )
    failed_task = _task_with_context(
        task,
        status=(
            CollectionTaskStatus.RETRY_SCHEDULED if should_retry else CollectionTaskStatus.FAILED
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
            "claim_token": None,
        },
    )
    repository.update_collection_task(
        failed_task,
        expected_claim_token=claim_token,
    )
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


def _collection_task_claim_token(task: CollectionTask) -> str:
    claim_token = task.context.get("claim_token")
    if not isinstance(claim_token, str) or not claim_token:
        raise CollectionTaskClaimLostError("collection_task_claim_lost")
    return claim_token


def _classify_failure(error: Exception) -> CollectionTaskFailure:
    message = stable_error(error)
    if isinstance(error, InstagramGraphConfigurationError):
        return CollectionTaskFailure(
            code=message,
            message=message,
            retryable=False,
        )
    if isinstance(error, InstagramGraphAccessError) and message in {
        "instagram_graph_http_400",
        "instagram_graph_http_401",
        "instagram_graph_http_403",
        "instagram_graph_error_10",
        "instagram_graph_error_100",
        "instagram_graph_error_190",
        "instagram_graph_invalid_response",
    }:
        return CollectionTaskFailure(
            code=message,
            message=message,
            retryable=False,
        )
    if isinstance(error, RedditOAuthConfigurationError):
        return CollectionTaskFailure(
            code="reddit_oauth_configuration_error",
            message=message,
            retryable=False,
        )
    if isinstance(error, RedditOAuthTokenError):
        return CollectionTaskFailure(
            code="reddit_oauth_token_error",
            message=message,
            retryable=False,
        )
    if isinstance(error, RedditUpstreamAccessError) and message in {
        "reddit_upstream_http_401",
        "reddit_upstream_http_403",
    }:
        return CollectionTaskFailure(
            code="reddit_capture_requires_authorized_access",
            message=message,
            retryable=False,
        )
    if message in {
        "collection_task_platform_unsupported",
        "collection_task_capture_method_unsupported",
        "platform_disabled_by_settings",
        "reddit_json_proxy_disabled_by_settings",
        "instagram_fixture_mode_disabled_by_settings",
        "instagram_fixture_payload_required",
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


def _platform_task_runtime_settings(
    *,
    repository: SqlAlchemyRepository,
    platform: Platform,
    config: CollectionTaskWorkerConfig,
) -> PlatformTaskRuntimeSettings:
    setting = repository.get_platform_setting(platform)
    if setting is not None:
        return PlatformTaskRuntimeSettings(
            enabled=setting.enabled,
            source=setting.source.value,
            config=_operational_platform_config(
                platform=platform,
                raw_config=setting.config,
                worker_config=config,
            ),
        )
    return PlatformTaskRuntimeSettings(
        enabled=_default_platform_enabled(platform),
        source="default",
        config=_default_operational_platform_config(platform, config),
    )


def _default_platform_enabled(platform: Platform) -> bool:
    return platform in {Platform.AMAZON, Platform.REDDIT, Platform.INSTAGRAM}


def _operational_platform_config(
    *,
    platform: Platform,
    raw_config: dict[str, JsonValue],
    worker_config: CollectionTaskWorkerConfig,
) -> dict[str, JsonValue]:
    if platform == Platform.AMAZON:
        return {
            "page_limit": _context_int(
                raw_config.get("page_limit"),
                fallback=worker_config.amazon_page_limit,
                minimum=1,
                maximum=20,
            ),
            "marketplaces": _context_string_list(
                raw_config.get("marketplaces"),
                fallback=["US", "UK", "DE", "CA", "AU", "JP"],
            ),
        }
    if platform == Platform.REDDIT:
        return {
            "json_proxy_enabled": _context_bool(
                raw_config.get("json_proxy_enabled"),
                fallback=True,
            ),
            "max_comment_depth": _context_int(
                raw_config.get("max_comment_depth"),
                fallback=worker_config.reddit_max_comment_depth,
                minimum=0,
                maximum=10,
            ),
        }
    return {
        "fixture_mode_enabled": _context_bool(
            raw_config.get("fixture_mode_enabled"),
            fallback=worker_config.instagram_fixture_mode_enabled,
        ),
        "graph_api_version": _context_string(
            raw_config.get("graph_api_version"),
            fallback=worker_config.instagram_graph_api_version,
        ),
        "comment_limit": _context_int(
            raw_config.get("comment_limit"),
            fallback=worker_config.instagram_graph_comment_limit,
            minimum=1,
            maximum=100,
        ),
    }


def _default_operational_platform_config(
    platform: Platform,
    config: CollectionTaskWorkerConfig,
) -> dict[str, JsonValue]:
    return _operational_platform_config(
        platform=platform,
        raw_config={},
        worker_config=config,
    )


def _context_object(value: JsonValue | None) -> dict[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def _context_bool(value: JsonValue | None, *, fallback: bool) -> bool:
    return value if isinstance(value, bool) else fallback


def _context_int(
    value: JsonValue | None,
    *,
    fallback: int,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, int) and minimum <= value <= maximum:
        return value
    return fallback


def _context_string(value: JsonValue | None, *, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback


def _context_string_list(
    value: JsonValue | None,
    *,
    fallback: list[JsonValue],
) -> list[JsonValue]:
    if not isinstance(value, list):
        return fallback
    strings: list[JsonValue] = [
        item.strip().upper() for item in value if isinstance(item, str) and item.strip()
    ]
    return strings if strings else fallback


def _limit_instagram_comment_payload(
    payload: dict[str, JsonValue],
    comment_limit: int,
) -> dict[str, JsonValue]:
    limited_payload = dict(payload)
    comments = limited_payload.get("comments")
    if isinstance(comments, dict):
        limited_payload["comments"] = _limited_comments_object(comments, comment_limit)
        return limited_payload
    if "data" in limited_payload:
        return _limited_comments_object(limited_payload, comment_limit)
    return limited_payload


def _limited_comments_object(
    comments: dict[str, JsonValue],
    comment_limit: int,
) -> dict[str, JsonValue]:
    limited_comments = dict(comments)
    data = limited_comments.get("data")
    if isinstance(data, list):
        limited_comments["data"] = data[:comment_limit]
    return limited_comments


def _configured_instagram_graph_fetcher(
    fetcher: InstagramGraphCommentsFetcher,
    *,
    graph_api_version: str,
    comment_limit: int,
) -> InstagramGraphCommentsFetcher:
    if isinstance(fetcher, InstagramGraphCommentsFetcherClient):
        return fetcher.with_config_overrides(
            api_version=graph_api_version,
            comment_limit=comment_limit,
        )
    return fetcher

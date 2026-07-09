from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.routes.capture_authorizations import (
    router as capture_authorizations_router,
)
from plugin_hub_api.routes.capture_capabilities import router as capture_capabilities_router
from plugin_hub_api.routes.collection_runs import router as collection_runs_router
from plugin_hub_api.routes.collection_tasks import router as collection_tasks_router
from plugin_hub_api.routes.insights import router as insights_router
from plugin_hub_api.routes.instagram_media_captures import router as instagram_media_captures_router
from plugin_hub_api.routes.platform_settings import router as platform_settings_router
from plugin_hub_api.routes.reddit_thread_captures import router as reddit_thread_captures_router
from plugin_hub_api.services.collection_task_worker import CollectionTaskWorkerConfig
from plugin_hub_api.services.instagram_graph_capture import (
    build_configured_instagram_graph_comments_fetcher,
)
from plugin_hub_api.services.reddit_capture import build_configured_reddit_json_fetcher


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings()
    resolved_database_url = database_url or settings.database_url
    engine = build_engine(resolved_database_url)
    init_database(engine)

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
        max_age=600,
    )
    app.state.engine = engine
    app.state.settings = settings
    app.state.session_factory = make_session_factory(engine)
    app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        max_attempts=settings.collection_task_max_attempts,
        retry_delay_seconds=settings.collection_task_retry_delay_seconds,
        worker_id=settings.collection_task_worker_id,
        claim_ttl_seconds=settings.collection_task_claim_ttl_seconds,
        instagram_graph_live_read_enabled=settings.instagram_graph_live_read_enabled,
        instagram_graph_api_version=settings.instagram_graph_api_version,
        instagram_graph_comment_limit=settings.instagram_graph_comment_limit,
    )
    app.state.reddit_json_fetcher = build_configured_reddit_json_fetcher(settings)
    app.state.instagram_graph_comments_fetcher = build_configured_instagram_graph_comments_fetcher(
        settings
    )
    app.state.instagram_graph_live_read_enabled = settings.instagram_graph_live_read_enabled
    app.include_router(capture_authorizations_router, prefix="/api")
    app.include_router(capture_capabilities_router, prefix="/api")
    app.include_router(collection_runs_router, prefix="/api")
    app.include_router(collection_tasks_router, prefix="/api")
    app.include_router(instagram_media_captures_router, prefix="/api")
    app.include_router(platform_settings_router, prefix="/api")
    app.include_router(reddit_thread_captures_router, prefix="/api")
    app.include_router(insights_router, prefix="/api/insights")
    return app

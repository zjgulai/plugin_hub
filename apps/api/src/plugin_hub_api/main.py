from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.routes.capture_authorizations import (
    router as capture_authorizations_router,
)
from plugin_hub_api.routes.capture_capabilities import router as capture_capabilities_router
from plugin_hub_api.routes.collection_runs import router as collection_runs_router
from plugin_hub_api.routes.collection_tasks import router as collection_tasks_router
from plugin_hub_api.routes.data_assets import router as data_assets_router
from plugin_hub_api.routes.insights import router as insights_router
from plugin_hub_api.routes.instagram_media_captures import router as instagram_media_captures_router
from plugin_hub_api.routes.platform_settings import router as platform_settings_router
from plugin_hub_api.routes.reddit_thread_captures import router as reddit_thread_captures_router
from plugin_hub_api.security import API_KEY_HEADER_NAME, require_api_access
from plugin_hub_api.services.collection_task_worker import CollectionTaskWorkerConfig
from plugin_hub_api.services.instagram_graph_capture import (
    build_configured_instagram_graph_comments_fetcher,
)
from plugin_hub_api.services.reddit_capture import build_configured_reddit_json_fetcher


def create_app(
    database_url: str | None = None,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    resolved_settings = settings if settings is not None else Settings()
    resolved_settings.validate_api_auth_configuration()
    resolved_database_url = database_url or resolved_settings.database_url
    engine = build_engine(
        resolved_database_url,
        sqlite_busy_timeout_ms=resolved_settings.sqlite_busy_timeout_ms,
        sqlite_wal_enabled=resolved_settings.sqlite_wal_enabled,
    )
    init_database(engine)

    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=resolved_settings.trusted_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allow_origins,
        allow_origin_regex=resolved_settings.cors_allow_origin_regex,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", API_KEY_HEADER_NAME, "Idempotency-Key"],
        max_age=600,
    )
    app.state.engine = engine
    app.state.settings = resolved_settings
    app.state.session_factory = make_session_factory(engine)
    app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        max_attempts=resolved_settings.collection_task_max_attempts,
        retry_delay_seconds=resolved_settings.collection_task_retry_delay_seconds,
        worker_id=resolved_settings.collection_task_worker_id,
        claim_ttl_seconds=resolved_settings.collection_task_claim_ttl_seconds,
        instagram_graph_live_read_enabled=resolved_settings.instagram_graph_live_read_enabled,
        instagram_graph_api_version=resolved_settings.instagram_graph_api_version,
        instagram_graph_comment_limit=resolved_settings.instagram_graph_comment_limit,
    )
    app.state.reddit_json_fetcher = build_configured_reddit_json_fetcher(resolved_settings)
    app.state.instagram_graph_comments_fetcher = build_configured_instagram_graph_comments_fetcher(
        resolved_settings
    )
    app.state.instagram_graph_live_read_enabled = (
        resolved_settings.instagram_graph_live_read_enabled
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    def readyz() -> dict[str, str]:
        with app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ready"}

    protected = [Depends(require_api_access)]
    app.include_router(capture_authorizations_router, prefix="/api", dependencies=protected)
    app.include_router(capture_capabilities_router, prefix="/api", dependencies=protected)
    app.include_router(collection_runs_router, prefix="/api", dependencies=protected)
    app.include_router(collection_tasks_router, prefix="/api", dependencies=protected)
    app.include_router(data_assets_router, prefix="/api", dependencies=protected)
    app.include_router(instagram_media_captures_router, prefix="/api", dependencies=protected)
    app.include_router(platform_settings_router, prefix="/api", dependencies=protected)
    app.include_router(reddit_thread_captures_router, prefix="/api", dependencies=protected)
    app.include_router(insights_router, prefix="/api/insights", dependencies=protected)
    return app

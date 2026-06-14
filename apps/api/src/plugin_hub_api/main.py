from __future__ import annotations

from fastapi import FastAPI

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.routes.collection_runs import router as collection_runs_router
from plugin_hub_api.routes.collection_tasks import router as collection_tasks_router
from plugin_hub_api.routes.insights import router as insights_router
from plugin_hub_api.services.collection_task_worker import CollectionTaskWorkerConfig


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings()
    resolved_database_url = database_url or settings.database_url
    engine = build_engine(resolved_database_url)
    init_database(engine)

    app = FastAPI()
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        max_attempts=settings.collection_task_max_attempts,
        retry_delay_seconds=settings.collection_task_retry_delay_seconds,
        worker_id=settings.collection_task_worker_id,
        claim_ttl_seconds=settings.collection_task_claim_ttl_seconds,
    )
    app.include_router(collection_runs_router, prefix="/api")
    app.include_router(collection_tasks_router, prefix="/api")
    app.include_router(insights_router, prefix="/api/insights")
    return app

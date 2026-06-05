from __future__ import annotations

from fastapi import FastAPI

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.routes.collection_runs import router as collection_runs_router


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings()
    resolved_database_url = database_url or settings.database_url
    engine = build_engine(resolved_database_url)
    init_database(engine)

    app = FastAPI()
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.include_router(collection_runs_router, prefix="/api")
    return app

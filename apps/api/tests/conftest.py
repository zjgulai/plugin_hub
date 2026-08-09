from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from plugin_hub_api.config import Settings
from plugin_hub_api.main import create_app
from plugin_hub_api.migrations import apply_pending_migrations


@pytest.fixture
def client() -> Generator[TestClient]:
    settings = Settings(
        api_auth_mode="disabled",
        sqlite_busy_timeout_ms=10_000,
        sqlite_wal_enabled=False,
        trusted_hosts=["testserver"],
    )
    app = create_app(database_url="sqlite+pysqlite:///:memory:", settings=settings)
    apply_pending_migrations(app.state.engine)
    with TestClient(app) as test_client:
        yield test_client

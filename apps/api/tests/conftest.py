from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from plugin_hub_api.main import create_app


@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(create_app(database_url="sqlite+pysqlite:///:memory:")) as test_client:
        yield test_client

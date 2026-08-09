from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from plugin_hub_api.config import Settings
from plugin_hub_api.main import create_app
from plugin_hub_api.security import _matches, require_api_access

READ_KEY = "r" * 32
WRITE_KEY = "w" * 32
API_KEY_HEADER = "X-Plugin-Hub-Api-Key"


def test_default_trusted_hosts_exclude_test_only_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PLUGIN_HUB_TRUSTED_HOSTS", raising=False)

    assert "testserver" not in Settings().trusted_hosts


@pytest.fixture
def protected_client() -> Generator[TestClient]:
    settings = Settings(
        api_auth_mode="required",
        api_read_key=READ_KEY,
        api_write_key=WRITE_KEY,
        trusted_hosts=["testserver"],
    )
    with TestClient(
        create_app(database_url="sqlite+pysqlite:///:memory:", settings=settings)
    ) as client:
        yield client


def test_required_auth_rejects_anonymous_api_reads(protected_client: TestClient) -> None:
    response = protected_client.get("/api/voc-units")

    assert response.status_code == 401
    assert response.json()["detail"] == "api_key_required"


def test_read_key_can_read_but_cannot_write(protected_client: TestClient) -> None:
    read_response = protected_client.get(
        "/api/voc-units",
        headers={API_KEY_HEADER: READ_KEY},
    )
    write_response = protected_client.post(
        "/api/collection-runs",
        headers={API_KEY_HEADER: READ_KEY},
        json={},
    )

    assert read_response.status_code == 200
    assert write_response.status_code == 401
    assert write_response.json()["detail"] == "api_write_key_required"


def test_write_key_can_access_write_route_before_payload_validation(
    protected_client: TestClient,
) -> None:
    response = protected_client.post(
        "/api/collection-runs",
        headers={API_KEY_HEADER: WRITE_KEY},
        json={},
    )

    assert response.status_code == 422


def test_openapi_declares_api_key_security_for_all_api_operations(
    protected_client: TestClient,
) -> None:
    spec = protected_client.get("/openapi.json").json()

    assert "APIKeyHeader" in spec["components"]["securitySchemes"]
    operations = [
        operation
        for path, path_item in spec["paths"].items()
        if path.startswith("/api/")
        for method, operation in path_item.items()
        if method in {"get", "post", "patch", "put", "delete"}
    ]
    assert operations
    assert all(operation.get("security") for operation in operations)


def test_required_auth_configuration_rejects_missing_keys() -> None:
    settings = Settings(api_auth_mode="required")

    with pytest.raises(ValueError, match="api_auth_keys_required"):
        create_app(database_url="sqlite+pysqlite:///:memory:", settings=settings)


@pytest.mark.parametrize("runtime_settings", [None, object()])
def test_api_security_fails_closed_without_valid_runtime_settings(
    runtime_settings: object | None,
) -> None:
    app = FastAPI()
    if runtime_settings is not None:
        app.state.settings = runtime_settings

    @app.get("/api/protected", dependencies=[Depends(require_api_access)])
    def protected_route() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/api/protected")

    assert response.status_code == 503
    assert response.json()["detail"] == "api_runtime_settings_unavailable"


def test_required_auth_normalizes_surrounding_whitespace_in_configured_keys() -> None:
    settings = Settings(
        api_auth_mode="required",
        api_read_key=f"  {READ_KEY}\n",
        api_write_key=f"\t{WRITE_KEY}  ",
        trusted_hosts=["testserver"],
    )

    with TestClient(
        create_app(database_url="sqlite+pysqlite:///:memory:", settings=settings)
    ) as client:
        read_response = client.get(
            "/api/voc-units",
            headers={API_KEY_HEADER: READ_KEY},
        )
        write_response = client.post(
            "/api/collection-runs",
            headers={API_KEY_HEADER: WRITE_KEY},
            json={},
        )

    assert read_response.status_code == 200
    assert write_response.status_code == 422


def test_api_key_comparison_rejects_non_ascii_input_without_raising() -> None:
    assert _matches("密钥", READ_KEY) is False
    assert _matches(READ_KEY, READ_KEY) is True


def test_api_responses_set_non_cacheable_security_headers(protected_client: TestClient) -> None:
    response = protected_client.get(
        "/api/voc-units",
        headers={API_KEY_HEADER: READ_KEY},
    )

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"

from fastapi.testclient import TestClient


def test_reddit_origin_can_preflight_collection_run_upload(client: TestClient) -> None:
    response = client.options(
        "/api/collection-runs",
        headers={
            "Origin": "https://www.reddit.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://www.reddit.com"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]


def test_chrome_extension_origin_can_preflight_collection_run_upload(client: TestClient) -> None:
    extension_origin = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef"
    response = client.options(
        "/api/collection-runs",
        headers={
            "Origin": extension_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == extension_origin

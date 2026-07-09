from __future__ import annotations

from fastapi.testclient import TestClient


def test_platform_settings_returns_defaults_without_sensitive_values(client: TestClient) -> None:
    response = client.get("/api/platform-settings")

    assert response.status_code == 200
    body = response.json()
    assert "token" not in str(body).lower()
    assert [item["platform"] for item in body["items"]] == ["amazon", "reddit", "instagram"]

    amazon = _setting(body, "amazon")
    assert amazon["enabled"] is True
    assert amazon["source"] == "default"
    assert amazon["config"]["page_limit"] == 3

    instagram = _setting(body, "instagram")
    assert instagram["enabled"] is False
    assert instagram["config"]["graph_api_version"] == "v25.0"
    assert instagram["config"]["comment_limit"] == 50


def test_platform_setting_patch_persists_and_records_audit(client: TestClient) -> None:
    update_response = client.patch(
        "/api/platform-settings/reddit",
        json={
            "enabled": False,
            "updated_by": "pytest",
            "config": {
                "json_proxy_enabled": True,
                "max_comment_depth": 5,
                "notes": "Use JSON endpoint only.",
            },
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["platform"] == "reddit"
    assert updated["enabled"] is False
    assert updated["source"] == "stored"
    assert updated["updated_by"] == "pytest"
    assert updated["config"]["max_comment_depth"] == 5

    get_response = client.get("/api/platform-settings/reddit")
    assert get_response.status_code == 200
    assert get_response.json()["config"]["notes"] == "Use JSON endpoint only."

    audit_response = client.get("/api/platform-settings/reddit/audit-events")
    assert audit_response.status_code == 200
    audit_items = audit_response.json()["items"]
    assert len(audit_items) == 1
    assert audit_items[0]["changed_by"] == "pytest"
    assert audit_items[0]["changed_fields"] == [
        "enabled",
        "config.max_comment_depth",
        "config.notes",
    ]
    assert audit_items[0]["previous_enabled"] is True
    assert audit_items[0]["new_enabled"] is False


def test_platform_setting_patch_rejects_sensitive_config_keys(client: TestClient) -> None:
    response = client.patch(
        "/api/platform-settings/instagram",
        json={
            "updated_by": "pytest",
            "config": {
                "access_token": "should-not-be-accepted",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "sensitive_config_key_not_allowed"


def test_platform_setting_patch_rejects_unknown_and_out_of_range_config(
    client: TestClient,
) -> None:
    unknown_response = client.patch(
        "/api/platform-settings/amazon",
        json={
            "updated_by": "pytest",
            "config": {
                "page_limit": 2,
                "marketplaces": ["US"],
                "notes": "",
                "crawl_budget": 99,
            },
        },
    )

    assert unknown_response.status_code == 422
    assert unknown_response.json()["detail"] == "unknown_config_key:crawl_budget"

    range_response = client.patch(
        "/api/platform-settings/amazon",
        json={
            "updated_by": "pytest",
            "config": {
                "page_limit": 0,
                "marketplaces": ["US"],
                "notes": "",
            },
        },
    )

    assert range_response.status_code == 422
    assert range_response.json()["detail"] == "page_limit_out_of_range"


def _setting(body: dict[str, object], platform: str) -> dict[str, object]:
    items = body["items"]
    assert isinstance(items, list)
    for item in items:
        assert isinstance(item, dict)
        if item["platform"] == platform:
            return item
    raise AssertionError(f"setting not found: {platform}")

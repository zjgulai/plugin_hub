from __future__ import annotations

from fastapi.testclient import TestClient


def test_capture_capabilities_reports_instagram_graph_authorization_gate(
    client: TestClient,
) -> None:
    response = client.get("/api/capture-capabilities")

    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in str(body)

    graph_capability = _capability(body, "instagram", "server_instagram_graph_comments")
    assert graph_capability["configured"] is False
    assert graph_capability["requires_authorization"] is True
    assert graph_capability["live_read_enabled"] is False
    assert graph_capability["live_write_enabled"] is False
    assert graph_capability["status"] == "credential_missing"
    assert graph_capability["evidence_grade"] == "L1-public-or-runtime"
    assert (
        graph_capability["next_required_action"]
        == "confirm_data_rights_then_configure_backend_only_meta_token"
    )
    assert (
        graph_capability["side_effect_boundary"]
        == "capability_read_only_no_meta_graph_call_no_production_write"
    )
    assert graph_capability["required_context_keys"] == [
        "media_id",
        "authorization_scope",
        "authorized_by",
        "authorized_at",
        "environment",
        "production_write",
    ]


def test_capture_capabilities_reports_live_read_blocked_when_only_fetcher_exists(
    client: TestClient,
) -> None:
    client.app.state.instagram_graph_comments_fetcher = lambda media_id: {
        "data": [],
        "media_id": media_id,
    }

    response = client.get("/api/capture-capabilities")

    assert response.status_code == 200
    graph_capability = _capability(response.json(), "instagram", "server_instagram_graph_comments")
    assert graph_capability["configured"] is True
    assert graph_capability["live_read_enabled"] is False
    assert graph_capability["status"] == "live_read_blocked"
    assert (
        graph_capability["next_required_action"]
        == "obtain_explicit_live_read_approval_then_enable_backend_switch"
    )


def test_capture_capabilities_reports_task_authorization_gate_when_live_read_is_enabled(
    client: TestClient,
) -> None:
    client.app.state.instagram_graph_comments_fetcher = lambda media_id: {
        "data": [],
        "media_id": media_id,
    }
    client.app.state.instagram_graph_live_read_enabled = True

    response = client.get("/api/capture-capabilities")

    assert response.status_code == 200
    graph_capability = _capability(response.json(), "instagram", "server_instagram_graph_comments")
    assert graph_capability["configured"] is True
    assert graph_capability["live_read_enabled"] is True
    assert graph_capability["status"] == "task_authorization_required"
    assert (
        graph_capability["next_required_action"]
        == "submit_task_authorization_context_to_preflight"
    )


def test_capture_capabilities_includes_existing_platform_methods(client: TestClient) -> None:
    response = client.get("/api/capture-capabilities")

    assert response.status_code == 200
    body = response.json()
    assert _capability(body, "amazon", "extension_dom_next_link_walk")["mode"] == "extension"
    assert _capability(body, "reddit", "server_reddit_json_proxy")["mode"] == "server"
    assert (
        _capability(body, "instagram", "server_instagram_fixture_payload")["status"]
        == "fixture_only"
    )
    assert (
        _capability(body, "instagram", "server_instagram_fixture_payload")[
            "side_effect_boundary"
        ]
        == "fixture_only_no_instagram_live_read"
    )


def _capability(body: dict[str, object], platform: str, capture_method: str) -> dict[str, object]:
    items = body["items"]
    assert isinstance(items, list)
    for item in items:
        assert isinstance(item, dict)
        if item["platform"] == platform and item["capture_method"] == capture_method:
            return item
    raise AssertionError(f"capability not found: {platform}/{capture_method}")

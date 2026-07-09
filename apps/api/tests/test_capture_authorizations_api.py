from __future__ import annotations

from fastapi.testclient import TestClient

VALID_INSTAGRAM_GRAPH_CONTEXT = {
    "media_id": "17900000000000001",
    "authorization_scope": "instagram_graph_live_read",
    "authorized_by": "local-test",
    "authorized_at": "2026-06-21T00:00:00Z",
    "environment": "local",
    "production_write": False,
}


def test_instagram_graph_live_read_preflight_reports_missing_credential(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/capture-authorizations/instagram-graph-live-read/preflight",
        json={"context": VALID_INSTAGRAM_GRAPH_CONTEXT},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in str(body)
    assert body["status"] == "credential_missing"
    assert body["configured"] is False
    assert body["live_read_enabled"] is False
    assert body["task_authorization_ready"] is True
    assert body["ready_for_worker"] is False
    assert body["missing_context_keys"] == []
    assert body["invalid_context_keys"] == []
    assert body["blocking_code"] is None
    assert body["evidence_grade"] == "L2-fixture-or-dry-run"
    assert (
        body["next_required_action"]
        == "confirm_data_rights_then_configure_backend_only_meta_token"
    )
    assert (
        body["side_effect_boundary"]
        == "dry_preflight_only_no_meta_graph_call_no_production_write"
    )


def test_instagram_graph_live_read_preflight_reports_live_read_blocked(
    client: TestClient,
) -> None:
    client.app.state.instagram_graph_comments_fetcher = lambda media_id: {
        "data": [],
        "media_id": media_id,
    }

    response = client.post(
        "/api/capture-authorizations/instagram-graph-live-read/preflight",
        json={"context": VALID_INSTAGRAM_GRAPH_CONTEXT},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "live_read_blocked"
    assert body["configured"] is True
    assert body["live_read_enabled"] is False
    assert body["task_authorization_ready"] is True
    assert body["ready_for_worker"] is False
    assert (
        body["next_required_action"]
        == "obtain_explicit_live_read_approval_then_enable_backend_switch"
    )


def test_instagram_graph_live_read_preflight_reports_context_gaps(
    client: TestClient,
) -> None:
    client.app.state.instagram_graph_comments_fetcher = lambda media_id: {
        "data": [],
        "media_id": media_id,
    }
    client.app.state.instagram_graph_live_read_enabled = True

    response = client.post(
        "/api/capture-authorizations/instagram-graph-live-read/preflight",
        json={
            "context": {
                "media_id": "17900000000000001",
                "authorization_scope": "wrong_scope",
                "environment": "unknown",
                "production_write": True,
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "task_authorization_required"
    assert body["configured"] is True
    assert body["live_read_enabled"] is True
    assert body["task_authorization_ready"] is False
    assert body["ready_for_worker"] is False
    assert body["missing_context_keys"] == ["authorized_by", "authorized_at"]
    assert body["invalid_context_keys"] == [
        "authorization_scope",
        "environment",
        "production_write",
    ]
    assert body["blocking_code"] == "instagram_graph_live_read_production_write_must_be_false"
    assert (
        body["next_required_action"]
        == "fix_task_authorization_context_before_worker_execution"
    )


def test_instagram_graph_live_read_preflight_reports_ready(
    client: TestClient,
) -> None:
    client.app.state.instagram_graph_comments_fetcher = lambda media_id: {
        "data": [],
        "media_id": media_id,
    }
    client.app.state.instagram_graph_live_read_enabled = True

    response = client.post(
        "/api/capture-authorizations/instagram-graph-live-read/preflight",
        json={"context": VALID_INSTAGRAM_GRAPH_CONTEXT},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["configured"] is True
    assert body["live_read_enabled"] is True
    assert body["task_authorization_ready"] is True
    assert body["ready_for_worker"] is True
    assert body["required_context_keys"] == [
        "media_id",
        "authorization_scope",
        "authorized_by",
        "authorized_at",
        "environment",
        "production_write",
    ]
    assert body["evidence_grade"] == "L2-fixture-or-dry-run"
    assert body["next_required_action"] == "run_authorized_read_only_task_only_after_approval"
    assert (
        body["side_effect_boundary"]
        == "dry_preflight_only_no_meta_graph_call_no_production_write"
    )


def test_instagram_graph_live_read_preflight_rejects_non_object_context(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/capture-authorizations/instagram-graph-live-read/preflight",
        json={"context": ["not", "an", "object"]},
    )

    assert response.status_code == 422

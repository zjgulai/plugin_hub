from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.schemas import CollectionTaskStatus
from plugin_hub_api.services.collection_task_worker import CollectionTaskWorkerConfig
from plugin_hub_api.services.instagram_graph_capture import InstagramGraphFetchResult
from plugin_hub_api.services.reddit_capture import RedditUpstreamAccessError

REDDIT_FIXTURE = Path(__file__).parents[3] / "tests" / "fixtures" / "reddit-thread.json"
INSTAGRAM_FIXTURE = (
    Path(__file__).parents[3] / "tests" / "fixtures" / "instagram-media-comments.json"
)
INSTAGRAM_GRAPH_AUTH_CONTEXT = {
    "authorization_scope": "instagram_graph_live_read",
    "authorized_by": "local-test",
    "authorized_at": "2026-06-21T00:00:00Z",
    "environment": "local",
    "production_write": False,
}


def test_post_reddit_collection_task_returns_pending_task(client: TestClient) -> None:
    response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "reddit_json_unavailable_dom_empty",
                "context": {
                    "thread_id": "thread123",
                    "json_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?raw_json=1",
                    "client_raw_item_count": 0,
                },
            }
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["collection_task_id"].startswith("task_")
    assert body["platform"] == "reddit"
    assert body["status"] == "pending"
    assert body["requested_capture_method"] == "server_reddit_json_proxy"
    assert body["trigger_reason"] == "reddit_json_unavailable_dom_empty"
    assert body["context"]["thread_id"] == "thread123"


def test_get_collection_tasks_lists_created_tasks(client: TestClient) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )

    assert create_response.status_code == 202

    list_response = client.get("/api/collection-tasks", params={"platform": "reddit"})

    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["collection_task_id"] == create_response.json()["collection_task_id"]
    assert items[0]["status"] == "pending"


def test_collection_task_rejects_non_object_context(client: TestClient) -> None:
    response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "reddit_json_unavailable_dom_empty",
                "context": ["not", "an", "object"],
            }
        },
    )

    assert response.status_code == 422


def test_run_reddit_collection_task_persists_collection_and_marks_completed(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "reddit_json_unavailable_dom_empty",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _fixture_fetcher

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "completed"
    assert body["collection_run_id"].startswith("run_")
    assert body["raw_item_count"] == 2
    assert body["voc_unit_count"] == 2
    assert body["task"]["context"]["collection_run_id"] == body["collection_run_id"]
    assert body["task"]["context"]["raw_item_count"] == 2

    voc_response = client.get("/api/voc-units", params={"platform": "reddit"})
    assert voc_response.status_code == 200
    items = voc_response.json()["items"]
    assert len(items) == 2
    assert {item["source_kind"] for item in items} == {"reddit_thread", "reddit_comment"}


def test_run_reddit_collection_task_applies_stored_max_comment_depth(
    client: TestClient,
) -> None:
    settings_response = client.patch(
        "/api/platform-settings/reddit",
        json={
            "enabled": True,
            "updated_by": "pytest",
            "config": {
                "json_proxy_enabled": True,
                "max_comment_depth": 0,
                "notes": "top-level only",
            },
        },
    )
    assert settings_response.status_code == 200
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _nested_reddit_payload_fetcher

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "completed"
    assert body["raw_item_count"] == 2
    assert body["task"]["context"]["platform_setting_source"] == "stored"
    assert body["task"]["context"]["platform_config_applied"]["max_comment_depth"] == 0
    assert body["task"]["context"]["max_comment_depth"] == 0

    voc_response = client.get("/api/voc-units", params={"platform": "reddit"})
    assert voc_response.status_code == 200
    source_ids = {item["source_object_id"] for item in voc_response.json()["items"]}
    assert "t1_top_level" in source_ids
    assert "t1_nested_reply" not in source_ids


def test_run_collection_task_respects_stored_platform_disabled_setting(
    client: TestClient,
) -> None:
    settings_response = client.patch(
        "/api/platform-settings/reddit",
        json={
            "enabled": False,
            "updated_by": "pytest",
            "config": {
                "json_proxy_enabled": True,
                "max_comment_depth": 8,
                "notes": "paused",
            },
        },
    )
    assert settings_response.status_code == 200
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _raising_fetcher

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert body["task"]["context"]["last_error_code"] == "platform_disabled_by_settings"
    assert body["task"]["context"]["retryable"] is False
    assert body["task"]["context"]["platform_enabled_at_run"] is False


def test_run_instagram_fixture_collection_task_persists_collection_and_marks_completed(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_fixture_payload",
                "trigger_reason": "fixture_contract_smoke",
                "context": {
                    "media_id": "17900000000000001",
                    "fixture_payload": json.loads(INSTAGRAM_FIXTURE.read_text()),
                },
            }
        },
    )
    assert create_response.status_code == 202

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "completed"
    assert body["collection_run_id"].startswith("run_")
    assert body["raw_item_count"] == 2
    assert body["voc_unit_count"] == 2
    assert body["task"]["context"]["collection_run_id"] == body["collection_run_id"]
    assert body["task"]["context"]["comment_count"] == 2

    voc_response = client.get("/api/voc-units", params={"platform": "instagram"})
    assert voc_response.status_code == 200
    items = voc_response.json()["items"]
    assert len(items) == 2
    assert {item["source_kind"] for item in items} == {"instagram_comment"}


def test_run_instagram_fixture_collection_task_applies_stored_comment_limit(
    client: TestClient,
) -> None:
    settings_response = client.patch(
        "/api/platform-settings/instagram",
        json={
            "enabled": True,
            "updated_by": "pytest",
            "config": {
                "fixture_mode_enabled": True,
                "graph_api_version": "v25.0",
                "comment_limit": 1,
                "notes": "single comment smoke",
            },
        },
    )
    assert settings_response.status_code == 200
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_fixture_payload",
                "trigger_reason": "fixture_contract_smoke",
                "context": {
                    "media_id": "17900000000000001",
                    "fixture_payload": json.loads(INSTAGRAM_FIXTURE.read_text()),
                },
            }
        },
    )
    assert create_response.status_code == 202

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "completed"
    assert body["raw_item_count"] == 1
    assert body["voc_unit_count"] == 1
    assert body["task"]["context"]["platform_setting_source"] == "stored"
    assert body["task"]["context"]["platform_config_applied"]["comment_limit"] == 1
    assert body["task"]["context"]["comment_limit"] == 1
    assert body["task"]["context"]["comment_count"] == 1


def test_run_instagram_fixture_collection_task_respects_fixture_mode_disabled(
    client: TestClient,
) -> None:
    settings_response = client.patch(
        "/api/platform-settings/instagram",
        json={
            "enabled": True,
            "updated_by": "pytest",
            "config": {
                "fixture_mode_enabled": False,
                "graph_api_version": "v25.0",
                "comment_limit": 50,
                "notes": "fixture disabled",
            },
        },
    )
    assert settings_response.status_code == 200
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_fixture_payload",
                "trigger_reason": "fixture_contract_smoke",
                "context": {
                    "media_id": "17900000000000001",
                    "fixture_payload": json.loads(INSTAGRAM_FIXTURE.read_text()),
                },
            }
        },
    )
    assert create_response.status_code == 202

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert (
        body["task"]["context"]["last_error_code"]
        == "instagram_fixture_mode_disabled_by_settings"
    )
    assert body["task"]["context"]["retryable"] is False


def test_run_instagram_fixture_collection_task_requires_fixture_payload(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_fixture_payload",
                "trigger_reason": "fixture_contract_smoke",
                "context": {"media_id": "17900000000000001"},
            }
        },
    )
    assert create_response.status_code == 202

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert body["task"]["context"]["last_error_code"] == "instagram_fixture_payload_required"
    assert body["task"]["context"]["retryable"] is False


def test_run_instagram_graph_collection_task_persists_collection_and_marks_completed(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_graph_comments",
                "trigger_reason": "authorized_graph_read",
                "context": {
                    "media_id": "17900000000000001",
                    **INSTAGRAM_GRAPH_AUTH_CONTEXT,
                },
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.instagram_graph_comments_fetcher = _instagram_graph_fetcher
    _enable_instagram_graph_live_read(client)

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "completed"
    assert body["collection_run_id"].startswith("run_")
    assert body["raw_item_count"] == 2
    assert body["voc_unit_count"] == 2
    assert body["task"]["context"]["collection_run_id"] == body["collection_run_id"]
    assert body["task"]["context"]["comment_count"] == 2
    assert body["task"]["context"]["graph_url"].startswith("https://graph.facebook.com/")
    assert "access_token" not in body["task"]["context"]["graph_url"]

    voc_response = client.get("/api/voc-units", params={"platform": "instagram"})
    assert voc_response.status_code == 200
    items = voc_response.json()["items"]
    assert len(items) == 2
    assert {item["source_kind"] for item in items} == {"instagram_comment"}
    assert items[0]["platform_extension"]["media_id"] == "17900000000000001"


def test_run_instagram_graph_collection_task_requires_configured_token(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_graph_comments",
                "trigger_reason": "authorized_graph_read",
                "context": {"media_id": "17900000000000001"},
            }
        },
    )
    assert create_response.status_code == 202

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert body["task"]["context"]["last_error_code"] == "instagram_graph_access_token_required"
    assert body["task"]["context"]["retryable"] is False


def test_run_instagram_graph_collection_task_requires_live_read_enabled(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_graph_comments",
                "trigger_reason": "authorized_graph_read",
                "context": {
                    "media_id": "17900000000000001",
                    **INSTAGRAM_GRAPH_AUTH_CONTEXT,
                },
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.instagram_graph_comments_fetcher = _blocked_instagram_graph_fetcher

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert body["task"]["context"]["last_error_code"] == "instagram_graph_live_read_not_enabled"
    assert body["task"]["context"]["retryable"] is False


def test_run_instagram_graph_collection_task_requires_task_authorization(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_graph_comments",
                "trigger_reason": "authorized_graph_read",
                "context": {"media_id": "17900000000000001"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.instagram_graph_comments_fetcher = _blocked_instagram_graph_fetcher
    _enable_instagram_graph_live_read(client)

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert (
        body["task"]["context"]["last_error_code"]
        == "instagram_graph_live_read_authorization_required"
    )
    assert body["task"]["context"]["retryable"] is False


def test_run_instagram_graph_collection_task_requires_production_write_false(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_graph_comments",
                "trigger_reason": "authorized_graph_read",
                "context": {
                    "media_id": "17900000000000001",
                    **INSTAGRAM_GRAPH_AUTH_CONTEXT,
                    "production_write": True,
                },
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.instagram_graph_comments_fetcher = _blocked_instagram_graph_fetcher
    _enable_instagram_graph_live_read(client)

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert (
        body["task"]["context"]["last_error_code"]
        == "instagram_graph_live_read_production_write_must_be_false"
    )
    assert body["task"]["context"]["retryable"] is False


def test_run_instagram_graph_collection_task_requires_media_id(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "instagram",
                "source_url": "https://www.instagram.com/p/example/",
                "requested_capture_method": "server_instagram_graph_comments",
                "trigger_reason": "authorized_graph_read",
                "context": {},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.instagram_graph_comments_fetcher = _instagram_graph_fetcher
    _enable_instagram_graph_live_read(client)

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert body["task"]["context"]["last_error_code"] == "instagram_graph_media_id_required"
    assert body["task"]["context"]["retryable"] is False


def test_run_reddit_collection_task_marks_failed_when_no_raw_items(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _empty_payload_fetcher

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert body["raw_item_count"] == 0
    assert body["voc_unit_count"] == 0
    assert body["task"]["context"]["error"] == "reddit_capture_no_raw_items"


def test_run_reddit_collection_task_schedules_retry_for_worker_error(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _raising_fetcher
    client.app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        max_attempts=3,
        retry_delay_seconds=60,
        worker_id="test-worker",
    )

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "retry_scheduled"
    assert body["task"]["context"]["attempt_count"] == 1
    assert body["task"]["context"]["max_attempts"] == 3
    assert body["task"]["context"]["worker_id"] == "test-worker"
    assert body["task"]["context"]["last_error_code"] == "collection_task_worker_error"
    assert body["task"]["context"]["retryable"] is True
    assert body["task"]["context"]["retry_scheduled"] is True
    assert isinstance(body["task"]["context"]["next_run_at"], str)


def test_run_reddit_collection_task_marks_403_as_authorization_blocker(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _access_denied_fetcher

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["collection_run_id"] is None
    assert body["task"]["context"]["last_error_code"] == "reddit_capture_requires_authorized_access"
    assert body["task"]["context"]["last_error_message"] == "reddit_upstream_http_403"
    assert body["task"]["context"]["retryable"] is False
    assert body["task"]["context"]["retry_scheduled"] is False
    assert body["task"]["context"]["next_run_at"] is None


def test_run_next_collection_task_processes_due_retry(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _raising_fetcher
    client.app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        max_attempts=3,
        retry_delay_seconds=0,
        worker_id="test-worker",
    )
    retry_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "retry_scheduled"
    client.app.state.reddit_json_fetcher = _fixture_fetcher

    run_next_response = client.post("/api/collection-tasks/run-next")

    assert run_next_response.status_code == 200
    body = run_next_response.json()
    assert body["status"] == "completed"
    assert body["task"]["context"]["attempt_count"] == 2
    assert body["task"]["context"]["collection_run_id"] == body["collection_run_id"]


def test_run_reddit_collection_task_marks_failed_after_max_attempts(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {
                    "thread_id": "thread123",
                    "attempt_count": 2,
                },
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _raising_fetcher
    client.app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        max_attempts=3,
        retry_delay_seconds=60,
        worker_id="test-worker",
    )

    run_response = client.post(
        f"/api/collection-tasks/{create_response.json()['collection_task_id']}/run"
    )

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "failed"
    assert body["task"]["context"]["attempt_count"] == 3
    assert body["task"]["context"]["retryable"] is True
    assert body["task"]["context"]["retry_scheduled"] is False
    assert body["task"]["context"]["next_run_at"] is None


def test_run_collection_task_returns_404_for_unknown_task(client: TestClient) -> None:
    response = client.post("/api/collection-tasks/task_missing/run")

    assert response.status_code == 404
    assert response.json()["detail"] == "collection_task_not_found"


def test_run_next_collection_task_processes_oldest_pending_task(client: TestClient) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    client.app.state.reddit_json_fetcher = _fixture_fetcher

    run_response = client.post("/api/collection-tasks/run-next")

    assert run_response.status_code == 200
    assert (
        run_response.json()["task"]["collection_task_id"]
        == create_response.json()["collection_task_id"]
    )
    assert run_response.json()["status"] == "completed"


def test_run_next_collection_task_skips_fresh_running_claim(client: TestClient) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["collection_task_id"]
    _set_running_task_claim_state(
        client=client,
        task_id=task_id,
        worker_id="fresh-worker",
        claim_expires_at=(datetime.now(tz=UTC) + timedelta(minutes=5)).isoformat(),
    )

    client.app.state.reddit_json_fetcher = _fixture_fetcher
    run_response = client.post("/api/collection-tasks/run-next")

    assert run_response.status_code == 404
    assert run_response.json()["detail"] == "pending_collection_task_not_found"

    list_response = client.get("/api/collection-tasks", params={"platform": "reddit"})
    assert list_response.status_code == 200
    task = list_response.json()["items"][0]
    assert task["collection_task_id"] == task_id
    assert task["status"] == "running"


def test_run_next_collection_task_recovers_stale_running_task(client: TestClient) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["collection_task_id"]
    stale_claimed_at = datetime.now(tz=UTC) - timedelta(minutes=10)
    _set_running_task_claim_state(
        client=client,
        task_id=task_id,
        worker_id="stale-worker",
        claim_expires_at=(stale_claimed_at - timedelta(minutes=1)).isoformat(),
        updated_at=stale_claimed_at,
    )
    client.app.state.reddit_json_fetcher = _fixture_fetcher
    client.app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        worker_id="recovery-worker"
    )

    run_response = client.post("/api/collection-tasks/run-next")

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "completed"
    assert body["task"]["collection_task_id"] == task_id
    assert body["task"]["context"]["claimed_by"] is None
    assert body["task"]["context"]["worker_id"] == "recovery-worker"


def test_claim_next_collection_task_prefers_single_worker_when_task_is_not_stale(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["collection_task_id"]

    now = datetime.now(tz=UTC)
    with client.app.state.session_factory() as session_a:
        first_repository = SqlAlchemyRepository(session_a)
        first_claim = first_repository.claim_next_runnable_collection_task(
            worker_id="worker-a",
            claim_ttl_seconds=600,
            now=now,
        )
    with client.app.state.session_factory() as session_b:
        second_repository = SqlAlchemyRepository(session_b)
        second_claim = second_repository.claim_next_runnable_collection_task(
            worker_id="worker-b",
            claim_ttl_seconds=600,
            now=now,
        )

    assert first_claim is not None
    assert first_claim.collection_task_id == task_id
    assert second_claim is None


def test_claim_next_collection_task_can_recover_stale_worker_claim(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["collection_task_id"]

    claim_started_at = datetime.now(tz=UTC)
    with client.app.state.session_factory() as session:
        repository = SqlAlchemyRepository(session)
        stale_task = repository.get_collection_task(task_id)
    assert stale_task is not None
    _set_running_task_claim_state(
        client=client,
        task_id=task_id,
        worker_id="worker-a",
        claim_expires_at=(claim_started_at - timedelta(seconds=1)).isoformat(),
        updated_at=claim_started_at,
    )

    with client.app.state.session_factory() as session_a:
        first_repository = SqlAlchemyRepository(session_a)
        first_claim = first_repository.claim_next_runnable_collection_task(
            worker_id="worker-a",
            claim_ttl_seconds=600,
            now=claim_started_at + timedelta(minutes=1),
        )
    assert first_claim is not None
    assert first_claim.collection_task_id == task_id


def test_run_next_collection_task_recovers_stale_running_task_when_claim_expires_missing(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/collection-tasks",
        json={
            "task": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "requested_capture_method": "server_reddit_json_proxy",
                "trigger_reason": "manual_retry",
                "context": {"thread_id": "thread123"},
            }
        },
    )
    assert create_response.status_code == 202
    task_id = create_response.json()["collection_task_id"]
    _set_running_task_claim_state(
        client=client,
        task_id=task_id,
        worker_id="stale-worker",
        claim_expires_at=None,
    )
    client.app.state.reddit_json_fetcher = _fixture_fetcher
    client.app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        worker_id="recovery-worker"
    )

    run_response = client.post("/api/collection-tasks/run-next")

    assert run_response.status_code == 200
    body = run_response.json()
    assert body["status"] == "completed"
    assert body["task"]["collection_task_id"] == task_id
    assert body["task"]["context"]["claimed_by"] is None
    assert body["task"]["context"]["worker_id"] == "recovery-worker"


def test_run_next_collection_task_returns_404_when_queue_is_empty(client: TestClient) -> None:
    response = client.post("/api/collection-tasks/run-next")

    assert response.status_code == 404
    assert response.json()["detail"] == "pending_collection_task_not_found"


def _set_running_task_claim_state(
    *,
    client: TestClient,
    task_id: str,
    worker_id: str,
    claim_expires_at: str | None,
    updated_at: datetime | None = None,
) -> None:
    updated_at = datetime.now(tz=UTC) if updated_at is None else updated_at
    with client.app.state.session_factory() as session:
        repository = SqlAlchemyRepository(session)
        task = repository.get_collection_task(task_id)
    assert task is not None
    updated_task = task.model_copy(
        update={
            "status": CollectionTaskStatus.RUNNING,
            "updated_at": updated_at,
            "context": {
                **task.context,
                "claimed_by": worker_id,
                "claimed_at": updated_at.isoformat(),
                "claim_expires_at": claim_expires_at,
            },
        }
    )
    with client.app.state.session_factory() as session:
        repository = SqlAlchemyRepository(session)
        repository.update_collection_task(updated_task)


def _fixture_fetcher(_url: str) -> object:
    return REDDIT_FIXTURE.read_text()


def _empty_payload_fetcher(_url: str) -> object:
    return [
        {"kind": "Listing", "data": {"children": []}},
        {"kind": "Listing", "data": {"children": []}},
    ]


def _nested_reddit_payload_fetcher(_url: str) -> object:
    return [
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "name": "t3_thread123",
                            "id": "thread123",
                            "title": "Example thread",
                            "selftext": "Thread body",
                            "author": "op",
                        },
                    }
                ]
            },
        },
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "name": "t1_top_level",
                            "id": "top_level",
                            "body": "Top level comment",
                            "author": "commenter_one",
                            "depth": 0,
                            "replies": {
                                "kind": "Listing",
                                "data": {
                                    "children": [
                                        {
                                            "kind": "t1",
                                            "data": {
                                                "name": "t1_nested_reply",
                                                "id": "nested_reply",
                                                "body": "Nested reply",
                                                "author": "commenter_two",
                                                "depth": 1,
                                            },
                                        }
                                    ]
                                },
                            },
                        },
                    }
                ]
            },
        },
    ]


def _raising_fetcher(_url: str) -> object:
    raise RuntimeError("reddit_upstream_unavailable")


def _access_denied_fetcher(_url: str) -> object:
    raise RedditUpstreamAccessError("reddit_upstream_http_403")


def _instagram_graph_fetcher(media_id: str) -> object:
    assert media_id == "17900000000000001"
    return InstagramGraphFetchResult(
        payload={
            "data": [
                {
                    "id": "18000000000000001",
                    "text": "This color is perfect.",
                    "username": "buyer_one",
                    "timestamp": "2026-06-05T10:01:00+0000",
                    "like_count": 4,
                },
                {
                    "id": "18000000000000002",
                    "text": "Does it come in a travel size?",
                    "username": "buyer_two",
                    "timestamp": "2026-06-05T10:02:00+0000",
                    "like_count": 1,
                },
            ]
        },
        graph_url="https://graph.facebook.com/v25.0/17900000000000001/comments?fields=id",
    )


def _blocked_instagram_graph_fetcher(media_id: str) -> object:
    raise AssertionError(f"instagram graph fetcher should not run for {media_id}")


def _enable_instagram_graph_live_read(client: TestClient) -> None:
    client.app.state.collection_task_worker_config = CollectionTaskWorkerConfig(
        instagram_graph_live_read_enabled=True
    )

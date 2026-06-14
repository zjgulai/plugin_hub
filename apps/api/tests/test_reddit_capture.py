from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from plugin_hub_api.schemas import SourceKind
from plugin_hub_api.services.reddit_capture import (
    build_reddit_json_url,
    parse_reddit_thread_json_payload,
)

REDDIT_FIXTURE = Path(__file__).parents[3] / "tests" / "fixtures" / "reddit-thread.json"


def test_build_reddit_json_url_adds_raw_json_without_losing_query() -> None:
    assert build_reddit_json_url(
        "https://www.reddit.com/r/Coffee/comments/thread123/example/?sort=confidence#comments"
    ) == "https://www.reddit.com/r/Coffee/comments/thread123/example/.json?sort=confidence&raw_json=1"


def test_parse_reddit_thread_json_payload_returns_thread_and_comment_raw_items() -> None:
    payload = json.loads(REDDIT_FIXTURE.read_text())

    raw_items, more_node_count, stop_reason = parse_reddit_thread_json_payload(
        payload=payload,
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
        captured_at=datetime(2026, 6, 14, tzinfo=UTC),
    )

    assert stop_reason is None
    assert more_node_count == 0
    assert [item.source_kind for item in raw_items] == [
        SourceKind.REDDIT_THREAD,
        SourceKind.REDDIT_COMMENT,
    ]
    assert raw_items[0].source_object_id == "t3_thread123"
    assert raw_items[1].raw_payload["link_id"] == "t3_thread123"
    assert raw_items[1].raw_payload["thread_id"] == "t3_thread123"
    assert raw_items[0].raw_payload_hash.startswith("sha256:")

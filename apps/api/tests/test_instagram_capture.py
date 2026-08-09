import json
from datetime import UTC, datetime
from pathlib import Path

from plugin_hub_api.schemas import Platform, SourceKind
from plugin_hub_api.services.instagram_capture import parse_instagram_media_comments_payload

INSTAGRAM_FIXTURE = (
    Path(__file__).parents[3] / "tests" / "fixtures" / "instagram-media-comments.json"
)


def test_parse_instagram_media_comments_payload_returns_comment_raw_items() -> None:
    payload = json.loads(INSTAGRAM_FIXTURE.read_text())

    raw_items, comment_count, stop_reason = parse_instagram_media_comments_payload(
        payload=payload,
        source_url="https://www.instagram.com/p/example/",
        captured_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    assert comment_count == 2
    assert stop_reason == "paging_next_not_fetched"
    assert [item.source_object_id for item in raw_items] == [
        "18000000000000001",
        "18000000000000002",
    ]
    assert {item.platform for item in raw_items} == {Platform.INSTAGRAM}
    assert {item.source_kind for item in raw_items} == {SourceKind.INSTAGRAM_COMMENT}
    assert raw_items[0].raw_payload["media_id"] == "17900000000000001"
    assert raw_items[0].raw_payload["permalink"] == "https://www.instagram.com/p/example/"
    assert raw_items[0].raw_payload_hash.startswith("sha256:")


def test_parse_instagram_media_comments_payload_rejects_invalid_shape() -> None:
    raw_items, comment_count, stop_reason = parse_instagram_media_comments_payload(
        payload={"comments": {"items": []}},
        source_url="https://www.instagram.com/p/example/",
        captured_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    assert raw_items == []
    assert comment_count == 0
    assert stop_reason == "missing_comments"


def test_parse_instagram_media_comments_payload_deduplicates_comment_ids() -> None:
    payload = json.loads(INSTAGRAM_FIXTURE.read_text())
    comments = payload["comments"]["data"]
    comments.append({**comments[0], "text": "duplicate transport record"})

    raw_items, comment_count, _ = parse_instagram_media_comments_payload(
        payload=payload,
        source_url="https://www.instagram.com/p/example/",
        captured_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    assert comment_count == 2
    assert len(raw_items) == 2
    assert len({item.source_object_id for item in raw_items}) == 2

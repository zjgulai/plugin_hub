from plugin_hub_api.schemas import Platform, SourceKind
from plugin_hub_api.services.etl import map_instagram_comment_to_voc


def test_maps_instagram_comment_to_canonical_voc_unit() -> None:
    voc = map_instagram_comment_to_voc(
        collection_run_id="run_ig_001",
        source_url="https://www.instagram.com/p/example/",
        raw_comment={
            "id": "18000000000000001",
            "text": "This pump is quiet enough for night sessions.",
            "username": "customer_one",
            "timestamp": "2026-06-05T08:30:00+0000",
            "media_id": "17900000000000001",
            "like_count": 4,
            "permalink": "https://www.instagram.com/p/example/",
            "captured_at": "2026-06-05T10:00:00+00:00",
        },
        coverage_confidence=0.86,
    )

    assert voc.platform == Platform.INSTAGRAM
    assert voc.source_kind == SourceKind.INSTAGRAM_COMMENT
    assert voc.source_object_id == "18000000000000001"
    assert voc.author_display == "customer_one"
    assert voc.body == "This pump is quiet enough for night sessions."
    assert voc.commercial_object_type == "instagram_media"
    assert voc.reply_role == "top_level_comment"
    assert voc.created_at is not None
    assert voc.created_at.isoformat() == "2026-06-05T08:30:00+00:00"
    assert voc.platform_extension["media_id"] == "17900000000000001"
    assert voc.platform_extension["like_count"] == 4
    assert voc.platform_extension["permalink"] == "https://www.instagram.com/p/example/"
    assert voc.quality_flags == []


def test_instagram_reply_comment_keeps_parent_context() -> None:
    voc = map_instagram_comment_to_voc(
        collection_run_id="run_ig_002",
        source_url="https://www.instagram.com/p/example/",
        raw_comment={
            "id": "18000000000000002",
            "text": "Does it work with larger bottles?",
            "username": "customer_two",
            "timestamp": "2026-06-05T09:00:00+0000",
            "media_id": "17900000000000001",
            "parent_id": "18000000000000001",
            "captured_at": "2026-06-05T10:00:00+00:00",
        },
        coverage_confidence=0.74,
    )

    assert voc.parent_id == "18000000000000001"
    assert voc.reply_role == "comment_reply"
    assert voc.platform_extension["parent_id"] == "18000000000000001"


def test_instagram_comment_missing_body_and_id_gets_quality_flags() -> None:
    voc = map_instagram_comment_to_voc(
        collection_run_id="run_ig_003",
        source_url="https://www.instagram.com/p/example/",
        raw_comment={
            "username": "customer_three",
            "timestamp": "not-a-time",
            "captured_at": "bad-captured-at",
        },
        coverage_confidence=0.5,
    )

    assert voc.source_object_id.startswith("instagram_missing_comment_id_")
    assert voc.body == ""
    assert "missing_instagram_comment_id" in voc.quality_flags
    assert "missing_body" in voc.quality_flags
    assert "invalid_instagram_timestamp" in voc.quality_flags
    assert "invalid_captured_at" in voc.quality_flags

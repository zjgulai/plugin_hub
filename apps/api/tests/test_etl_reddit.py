from plugin_hub_api.schemas import JsonValue, Platform, SourceKind
from plugin_hub_api.services.etl import (
    map_reddit_comment_to_voc,
    map_reddit_thread_to_voc,
)


def test_maps_reddit_thread_to_canonical_voc_unit() -> None:
    voc = map_reddit_thread_to_voc(
        collection_run_id="run_red_001",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
        raw_thread={
            "name": "t3_thread123",
            "id": "thread123",
            "subreddit": "Coffee",
            "subreddit_name_prefixed": "r/Coffee",
            "title": "Best grinder for espresso?",
            "selftext": "I want a quieter grinder under $300.",
            "author": "buyer_researcher",
            "created_utc": 1780602718.0,
            "score": 42,
            "upvote_ratio": 0.88,
            "num_comments": 12,
            "locked": False,
            "archived": False,
            "stickied": False,
            "link_flair_text": "Buying Advice",
        },
        coverage_confidence=0.95,
    )

    assert voc.platform == Platform.REDDIT
    assert voc.source_kind == SourceKind.REDDIT_THREAD
    assert voc.source_object_id == "t3_thread123"
    assert voc.thread_id == "t3_thread123"
    assert voc.reply_role == "thread_root"
    assert voc.title == "Best grinder for espresso?"
    assert voc.body == "I want a quieter grinder under $300."
    assert voc.author_display == "buyer_researcher"
    assert voc.created_at is not None
    assert voc.platform_extension["subreddit"] == "Coffee"
    assert voc.platform_extension["subreddit_name_prefixed"] == "r/Coffee"
    assert voc.platform_extension["post_flair"] == "Buying Advice"
    assert voc.platform_extension["upvote_ratio"] == 0.88
    assert voc.platform_extension["num_comments"] == 12


def test_maps_reddit_comment_parent_context() -> None:
    voc = map_reddit_comment_to_voc(
        collection_run_id="run_red_001",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/comment456/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_comment456",
            "id": "comment456",
            "body": "The motor noise is the real issue.",
            "author": "espresso_owner",
            "parent_id": "t1_parent999",
            "link_id": "t3_thread123",
            "depth": 2,
            "created_utc": 1780602800.0,
            "score": 7,
            "is_submitter": False,
            "controversiality": 0,
            "replies": "",
        },
        coverage_confidence=0.88,
    )

    assert voc.source_kind == SourceKind.REDDIT_COMMENT
    assert voc.thread_id == "t3_thread123"
    assert voc.parent_id == "t1_parent999"
    assert voc.depth == 2
    assert voc.reply_role == "nested_reply"
    assert voc.platform_extension["score"] == 7
    assert voc.platform_extension["link_id"] == "t3_thread123"


def test_reddit_more_node_is_not_treated_as_comment_body() -> None:
    voc = map_reddit_comment_to_voc(
        collection_run_id="run_red_002",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
        thread_id="t3_thread123",
        raw_comment={
            "kind": "more",
            "id": "more123",
            "parent_id": "t1_parent999",
            "children": ["abc", "def"],
            "depth": 1,
        },
        coverage_confidence=0.5,
    )

    assert voc.source_object_id == "more_more123"
    assert voc.body == ""
    assert "reddit_more_node" in voc.quality_flags
    assert voc.platform_extension["more_node_count"] == 2


def test_deleted_or_removed_comment_body_gets_quality_flag() -> None:
    deleted = map_reddit_comment_to_voc(
        collection_run_id="run_red_003",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/deleted/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_deleted",
            "body": "[deleted]",
            "parent_id": "t3_thread123",
        },
        coverage_confidence=0.7,
    )
    removed = map_reddit_comment_to_voc(
        collection_run_id="run_red_003",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/removed/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_removed",
            "body": "[removed]",
            "parent_id": "t3_thread123",
        },
        coverage_confidence=0.7,
    )

    assert deleted.body == "[deleted]"
    assert removed.body == "[removed]"
    assert "reddit_deleted_or_removed" in deleted.quality_flags
    assert "reddit_deleted_or_removed" in removed.quality_flags


def test_reddit_top_level_comment_reply_role_from_parent_or_depth() -> None:
    from_parent = map_reddit_comment_to_voc(
        collection_run_id="run_red_004",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/top1/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_top1",
            "body": "Parent is thread.",
            "parent_id": "t3_thread123",
            "depth": 3,
        },
        coverage_confidence=0.7,
    )
    from_depth = map_reddit_comment_to_voc(
        collection_run_id="run_red_004",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/top2/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_top2",
            "body": "Depth is zero.",
            "parent_id": "t1_parent999",
            "depth": 0,
        },
        coverage_confidence=0.7,
    )

    assert from_parent.reply_role == "top_level_reply"
    assert from_depth.reply_role == "top_level_reply"


def test_missing_reddit_comment_id_is_stable_and_flagged() -> None:
    raw_comment: dict[str, JsonValue] = {
        "body": "No identifier from parser.",
        "parent_id": "t3_thread123",
        "depth": 0,
    }

    first = map_reddit_comment_to_voc(
        collection_run_id="run_red_005",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/noid/",
        thread_id="t3_thread123",
        raw_comment=raw_comment,
        coverage_confidence=0.7,
    )
    second = map_reddit_comment_to_voc(
        collection_run_id="run_red_005",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/noid/",
        thread_id="t3_thread123",
        raw_comment={
            "depth": 0,
            "parent_id": "t3_thread123",
            "body": "No identifier from parser.",
        },
        coverage_confidence=0.7,
    )

    assert first.source_object_id.startswith("reddit_missing_comment_id_")
    assert first.source_object_id == second.source_object_id
    assert "missing_comment_id" in first.quality_flags


def test_invalid_reddit_created_utc_is_flagged_but_missing_is_not() -> None:
    invalid = map_reddit_comment_to_voc(
        collection_run_id="run_red_006",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/invalid-time/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_invalid_time",
            "body": "Bad timestamp.",
            "created_utc": "1780602800.0",
        },
        coverage_confidence=0.7,
    )
    missing = map_reddit_comment_to_voc(
        collection_run_id="run_red_006",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/missing-time/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_missing_time",
            "body": "No timestamp.",
        },
        coverage_confidence=0.7,
    )

    assert invalid.created_at is None
    assert "invalid_created_utc" in invalid.quality_flags
    assert missing.created_at is None
    assert "invalid_created_utc" not in missing.quality_flags


def test_invalid_reddit_created_utc_rejects_bool() -> None:
    voc = map_reddit_comment_to_voc(
        collection_run_id="run_red_007",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/bool-time/",
        thread_id="t3_thread123",
        raw_comment={
            "name": "t1_bool_time",
            "body": "Bool timestamp.",
            "created_utc": True,
        },
        coverage_confidence=0.7,
    )

    assert voc.created_at is None
    assert "invalid_created_utc" in voc.quality_flags


def test_thread_missing_name_uses_t3_id_and_missing_text_flags() -> None:
    voc = map_reddit_thread_to_voc(
        collection_run_id="run_red_008",
        source_url="https://www.reddit.com/r/Coffee/comments/thread_without_text/example/",
        raw_thread={
            "id": "thread_without_text",
            "created_utc": 1780602718,
        },
        coverage_confidence=0.9,
    )

    assert voc.source_object_id == "t3_thread_without_text"
    assert voc.thread_id == "t3_thread_without_text"
    assert voc.title is None
    assert voc.body == ""
    assert "missing_thread_title" in voc.quality_flags
    assert "missing_thread_body" in voc.quality_flags


def test_reddit_voc_model_dump_json_executes() -> None:
    voc = map_reddit_thread_to_voc(
        collection_run_id="run_red_009",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
        raw_thread={
            "name": "t3_thread123",
            "title": "Serializable thread",
            "selftext": "Body",
            "created_utc": 1780602718.0,
            "score": 1,
        },
        coverage_confidence=1.0,
    )

    assert voc.model_dump_json()

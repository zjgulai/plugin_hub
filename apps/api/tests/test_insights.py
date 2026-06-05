from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from plugin_hub_api.schemas import CanonicalVocUnit
from plugin_hub_api.services.insights import generate_strategy_notes


def test_generate_strategy_notes_groups_loud_and_noise_as_noise() -> None:
    notes = generate_strategy_notes(
        [
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RLOUD",
                body="The grinder is very loud during every morning use.",
                coverage_confidence=0.9,
            ),
            _voc_unit(
                platform="reddit",
                source_kind="reddit_comment",
                source_object_id="t1_noise",
                body="The motor noise makes it hard to use in an apartment.",
                coverage_confidence=0.7,
            ),
        ]
    )

    assert notes == [
        {
            "strategy_type": "voc_template",
            "topic": "noise",
            "evidence_count": 2,
            "evidence_examples": [
                "The grinder is very loud during every morning use.",
                "The motor noise makes it hard to use in an apartment.",
            ],
            "recommendation": (
                "Prioritize reducing noise complaints in product messaging and fixes."
            ),
            "evidence_strength": 0.7,
            "quality_flags": [],
        }
    ]


def test_generate_strategy_notes_preserves_low_quality_evidence_flags() -> None:
    notes = generate_strategy_notes(
        [
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RBROKEN",
                body="The lid broke after three days.",
                coverage_confidence=0.42,
                quality_flags=["missing_review_id", "invalid_created_at"],
            ),
            _voc_unit(
                platform="amazon",
                source_kind="amazon_review",
                source_object_id="RSTOPPED",
                body="It stopped working after one week.",
                coverage_confidence=0.83,
                quality_flags=["missing_review_id"],
            ),
        ]
    )

    note = notes[0]

    assert note["topic"] == "durability"
    assert note["evidence_count"] == 2
    assert note["evidence_strength"] == 0.42
    assert note["evidence_examples"] == [
        "The lid broke after three days.",
        "It stopped working after one week.",
    ]
    assert note["quality_flags"] == ["invalid_created_at", "missing_review_id"]


def test_get_strategy_notes_from_collection_runs_by_platform(client: TestClient) -> None:
    amazon_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="amazon",
                source_url="https://www.amazon.com/product-reviews/B000000001",
                coverage_confidence=0.64,
            ),
            "raw_items": [
                _amazon_review_item(
                    source_object_id="RLOUD",
                    body="The fan noise is loud enough to wake everyone.",
                    raw_payload_hash="sha256:amazon-loud",
                )
            ],
        },
    )
    reddit_response = client.post(
        "/api/collection-runs",
        json={
            "run": _collection_run(
                platform="reddit",
                source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
                coverage_confidence=0.91,
            ),
            "raw_items": [
                _reddit_thread_item(
                    body="The price is too expensive for a simple grinder.",
                )
            ],
        },
    )

    assert amazon_response.status_code == 201
    assert reddit_response.status_code == 201

    response = client.get("/api/insights/strategy-notes", params={"platform": "amazon"})

    assert response.status_code == 200
    notes = response.json()["items"]
    assert len(notes) == 1
    assert notes[0]["topic"] == "noise"
    assert notes[0]["evidence_strength"] == 0.64
    assert notes[0]["evidence_examples"] == [
        "The fan noise is loud enough to wake everyone."
    ]

    all_response = client.get("/api/insights/strategy-notes")

    assert all_response.status_code == 200
    all_notes = all_response.json()["items"]
    assert {note["topic"] for note in all_notes} == {"noise", "price"}


def _voc_unit(
    *,
    platform: str,
    source_kind: str,
    source_object_id: str,
    body: str,
    coverage_confidence: float,
    quality_flags: list[str] | None = None,
) -> CanonicalVocUnit:
    return CanonicalVocUnit.model_validate(
        {
            "platform": platform,
            "source_kind": source_kind,
            "source_object_id": source_object_id,
            "collection_run_id": "run_insights",
            "source_url": "https://example.com/source",
            "captured_at": "2026-06-05T00:00:00+00:00",
            "body": body,
            "quality_flags": quality_flags or [],
            "coverage_confidence": coverage_confidence,
        }
    )


def _collection_run(
    *,
    platform: str,
    source_url: str,
    coverage_confidence: float,
) -> dict[str, object]:
    return {
        "platform": platform,
        "source_url": source_url,
        "capture_method": "browser_extension",
        "coverage_scope": {"page": 1},
        "stop_reason": "manual_stop",
        "coverage_confidence": coverage_confidence,
    }


def _amazon_review_item(
    *,
    source_object_id: str,
    body: str,
    raw_payload_hash: str,
) -> dict[str, object]:
    return {
        "platform": "amazon",
        "source_kind": "amazon_review",
        "source_object_id": source_object_id,
        "raw_schema_version": "amazon-review-v1",
        "parser_version": "parser-v1",
        "raw_payload": {
            "review_id": source_object_id,
            "rating": 2,
            "body": body,
            "captured_at": "2026-06-05T00:00:00+00:00",
        },
        "raw_payload_hash": raw_payload_hash,
        "captured_at": datetime(2026, 6, 5, tzinfo=UTC).isoformat(),
    }


def _reddit_thread_item(*, body: str) -> dict[str, object]:
    return {
        "platform": "reddit",
        "source_kind": "reddit_thread",
        "source_object_id": "t3_thread123",
        "raw_schema_version": "reddit-thread-v1",
        "parser_version": "parser-v1",
        "raw_payload": {
            "name": "t3_thread123",
            "id": "thread123",
            "title": "Best grinder for espresso?",
            "selftext": body,
            "author": "buyer_researcher",
            "created_utc": 1780602718.0,
            "score": 42,
        },
        "raw_payload_hash": "sha256:reddit-thread123",
        "captured_at": datetime(2026, 6, 5, tzinfo=UTC).isoformat(),
    }

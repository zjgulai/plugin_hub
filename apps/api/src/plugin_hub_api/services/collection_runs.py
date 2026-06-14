from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    CollectionRun,
    JsonValue,
    RawSourceItem,
    SourceKind,
)
from plugin_hub_api.services.etl import (
    map_amazon_review_to_voc,
    map_reddit_comment_to_voc,
    map_reddit_thread_to_voc,
)


def map_raw_item_to_voc(*, run: CollectionRun, raw_item: RawSourceItem) -> CanonicalVocUnit:
    source_url = str(run.model_dump(mode="json")["source_url"])

    if raw_item.source_kind == SourceKind.AMAZON_REVIEW:
        return map_amazon_review_to_voc(
            collection_run_id=run.collection_run_id,
            source_url=source_url,
            raw_review=raw_item.raw_payload,
            coverage_confidence=run.coverage_confidence,
        )
    if raw_item.source_kind == SourceKind.REDDIT_THREAD:
        return map_reddit_thread_to_voc(
            collection_run_id=run.collection_run_id,
            source_url=source_url,
            raw_thread=raw_item.raw_payload,
            coverage_confidence=run.coverage_confidence,
        )
    return map_reddit_comment_to_voc(
        collection_run_id=run.collection_run_id,
        source_url=source_url,
        thread_id=reddit_comment_thread_id(raw_item.raw_payload),
        raw_comment=raw_item.raw_payload,
        coverage_confidence=run.coverage_confidence,
    )


def reddit_comment_thread_id(raw_payload: dict[str, JsonValue]) -> str:
    link_id = _optional_reddit_thread_fullname(raw_payload.get("link_id"))
    thread_id = _optional_reddit_thread_fullname(raw_payload.get("thread_id"))
    candidates = [value for value in (link_id, thread_id) if value is not None]
    if not candidates:
        _raise_reddit_comment_thread_id_required()

    if len(candidates) == 2 and candidates[0] != candidates[1]:
        _raise_reddit_comment_thread_id_required()

    return candidates[0]


def _optional_reddit_thread_fullname(value: JsonValue | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.startswith("t3_") and len(value) > len("t3_"):
        return value
    _raise_reddit_comment_thread_id_required()


def _raise_reddit_comment_thread_id_required() -> NoReturn:
    raise HTTPException(
        status_code=422,
        detail="reddit_comment_thread_id_required",
    )

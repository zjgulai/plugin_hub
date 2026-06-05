---
title: VOC 浏览器插件 MVP 实施计划
doc_type: workflow
module: workflows
topic: voc-browser-plugin-mvp-implementation
status: review
created: 2026-06-05
updated: 2026-06-05
owner: self
source: human+ai
---

# VOC Browser Plugin MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the P0 VOC browser plugin loop for Amazon and Reddit: browser capture, private backend ingest, schema ETL, VOC Hub, and traceable AI-style insight output.

**Architecture:** Use a monorepo with three focused apps: `apps/api` for FastAPI + Pydantic + SQLAlchemy, `apps/extension` for the Manifest V3 Chrome extension, and `apps/web` for the VOC Hub. Data contracts are owned by the backend and mirrored in the extension/web only after tests lock the schema.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic V2, SQLAlchemy 2.0, pytest, TypeScript strict mode, React 19, Next.js 15, Tailwind CSS, Zustand, Vitest, pnpm, uv.

---

## Scope Check

The PRD spans extension, backend, ETL, VOC Hub, and AI insight output. The plan keeps them in one ordered implementation track because each later subsystem depends on the same schema contract:

1. Repository and tooling baseline.
2. Backend data contracts and ETL.
3. Backend persistence and API.
4. Extension capture and upload.
5. VOC Hub and insight views.
6. End-to-end verification.

P0 excludes TikTok, Shopify, Seller Central, cloud robot execution, proxy pools, automatic bypassing of access controls, and full BI dashboards.

## File Structure

Create this structure:

```text
plugin_hub/
├─ README.md
├─ package.json
├─ pnpm-workspace.yaml
├─ docs/
│  ├─ product/
│  └─ workflows/
├─ apps/
│  ├─ api/
│  │  ├─ pyproject.toml
│  │  ├─ src/plugin_hub_api/
│  │  │  ├─ __init__.py
│  │  │  ├─ main.py
│  │  │  ├─ config.py
│  │  │  ├─ db.py
│  │  │  ├─ models.py
│  │  │  ├─ schemas.py
│  │  │  ├─ repositories.py
│  │  │  ├─ routes/
│  │  │  │  ├─ __init__.py
│  │  │  │  ├─ collection_runs.py
│  │  │  │  ├─ insights.py
│  │  │  │  └─ voc_units.py
│  │  │  └─ services/
│  │  │     ├─ __init__.py
│  │  │     ├─ etl.py
│  │  │     ├─ dedupe.py
│  │  │     └─ insights.py
│  │  └─ tests/
│  │     ├─ conftest.py
│  │     ├─ test_contracts.py
│  │     ├─ test_etl_amazon.py
│  │     ├─ test_etl_reddit.py
│  │     ├─ test_collection_runs_api.py
│  │     └─ test_insights.py
│  ├─ extension/
│  │  ├─ package.json
│  │  ├─ tsconfig.json
│  │  ├─ vite.config.ts
│  │  ├─ manifest.config.ts
│  │  ├─ src/
│  │  │  ├─ background/service-worker.ts
│  │  │  ├─ content/content-script.ts
│  │  │  ├─ lib/amazon-parser.ts
│  │  │  ├─ lib/reddit-parser.ts
│  │  │  ├─ lib/page-detect.ts
│  │  │  ├─ lib/upload-client.ts
│  │  │  ├─ popup/Popup.tsx
│  │  │  └─ types/contracts.ts
│  │  └─ tests/
│  │     ├─ amazon-parser.test.ts
│  │     ├─ reddit-parser.test.ts
│  │     ├─ page-detect.test.ts
│  │     └─ upload-client.test.ts
│  └─ web/
│     ├─ package.json
│     ├─ next.config.ts
│     ├─ tsconfig.json
│     ├─ app/
│     │  ├─ globals.css
│     │  ├─ layout.tsx
│     │  └─ page.tsx
│     ├─ src/
│     │  ├─ lib/api.ts
│     │  ├─ store/use-voc-filters.ts
│     │  └─ components/
│     │     ├─ InsightPanel.tsx
│     │     ├─ QualityBadge.tsx
│     │     ├─ VocEvidenceTable.tsx
│     │     └─ VocFilters.tsx
│     └─ tests/
│        ├─ api.test.ts
│        └─ voc-components.test.tsx
└─ tests/
   └─ fixtures/
      ├─ amazon-review-page.html
      └─ reddit-thread.json
```

## Task 1: Repository Tooling Baseline

**Files:**
- Create: `README.md`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/plugin_hub_api/__init__.py`

- [ ] **Step 1: Create root workspace files**

Create `package.json`:

```json
{
  "name": "plugin-hub",
  "private": true,
  "packageManager": "pnpm@9.15.4",
  "scripts": {
    "test": "pnpm -r test",
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r typecheck"
  },
  "devDependencies": {
    "typescript": "^5.8.3"
  }
}
```

Create `pnpm-workspace.yaml`:

```yaml
packages:
  - "apps/extension"
  - "apps/web"
```

Create `README.md`:

```md
# Plugin Hub

VOC-first Chrome extension and private backend for Amazon and Reddit customer voice collection.

## P0 Scope

- Amazon review capture
- Reddit thread capture
- Private backend ingest
- Schema-based VOC ETL
- VOC Hub review surface

## Local Apps

- `apps/api`: FastAPI backend
- `apps/extension`: Chrome extension
- `apps/web`: Next.js VOC Hub
```

- [ ] **Step 2: Create backend project file**

Create `apps/api/pyproject.toml`:

```toml
[project]
name = "plugin-hub-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "pydantic>=2.10.0",
  "pydantic-settings>=2.7.0",
  "sqlalchemy>=2.0.36",
  "uvicorn[standard]>=0.34.0",
]

[dependency-groups]
dev = [
  "httpx>=0.28.0",
  "pytest>=8.3.0",
  "pytest-asyncio>=0.25.0",
  "ruff>=0.9.0",
  "mypy>=1.14.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["plugin_hub_api"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Create `apps/api/src/plugin_hub_api/__init__.py`:

```python
"""Plugin Hub API package."""
```

- [ ] **Step 3: Install dependencies**

Run:

```bash
pnpm install
cd apps/api && uv sync
```

Expected: pnpm creates `pnpm-lock.yaml`; uv creates `apps/api/uv.lock`.

- [ ] **Step 4: Commit**

```bash
git add README.md package.json pnpm-workspace.yaml pnpm-lock.yaml apps/api/pyproject.toml apps/api/uv.lock apps/api/src/plugin_hub_api/__init__.py
git commit -m "搭建 VOC 插件 MVP 工程基线"
```

## Task 2: Backend Schema Contracts

**Files:**
- Create: `apps/api/src/plugin_hub_api/schemas.py`
- Create: `apps/api/tests/test_contracts.py`

- [ ] **Step 1: Write failing contract tests**

Create `apps/api/tests/test_contracts.py`:

```python
from datetime import UTC, datetime

from plugin_hub_api.schemas import (
    CanonicalVocUnit,
    CollectionRunCreate,
    Platform,
    RawSourceItem,
    SourceKind,
)


def test_collection_run_create_preserves_amazon_pagination_context() -> None:
    payload = CollectionRunCreate(
        platform=Platform.AMAZON,
        source_url="https://www.amazon.com/product-reviews/B000000001",
        capture_method="extension_dom",
        coverage_scope={"segment": "critical_1_2_star", "max_pages": 10},
        stop_reason="duplicate_page_hash",
        coverage_confidence=0.72,
    )

    assert payload.platform == Platform.AMAZON
    assert payload.coverage_scope["segment"] == "critical_1_2_star"
    assert payload.stop_reason == "duplicate_page_hash"


def test_raw_source_item_keeps_platform_schema_version() -> None:
    item = RawSourceItem(
        platform=Platform.REDDIT,
        source_kind=SourceKind.REDDIT_COMMENT,
        source_object_id="t1_comment123",
        raw_schema_version="raw_reddit_comment_v1",
        parser_version="reddit-json-parser@0.1.0",
        raw_payload={"id": "comment123", "parent_id": "t3_thread123"},
        raw_payload_hash="hash123",
        captured_at=datetime(2026, 6, 5, tzinfo=UTC),
    )

    assert item.raw_schema_version == "raw_reddit_comment_v1"
    assert item.raw_payload["parent_id"] == "t3_thread123"


def test_canonical_voc_unit_allows_platform_specific_context() -> None:
    voc = CanonicalVocUnit(
        platform=Platform.AMAZON,
        source_kind=SourceKind.AMAZON_REVIEW,
        source_object_id="R123",
        collection_run_id="run_001",
        source_url="https://www.amazon.com/review/R123",
        captured_at=datetime(2026, 6, 5, tzinfo=UTC),
        title="Great but noisy",
        body="The motor is strong, but it is louder than expected.",
        quality_flags=[],
        coverage_confidence=0.9,
        platform_extension={"rating": 4, "verified_purchase": True},
    )

    assert voc.platform_extension["rating"] == 4
    assert voc.body.startswith("The motor")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd apps/api && uv run pytest tests/test_contracts.py -v
```

Expected: FAIL with import error for `plugin_hub_api.schemas`.

- [ ] **Step 3: Implement schema contracts**

Create `apps/api/src/plugin_hub_api/schemas.py`:

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Platform(StrEnum):
    AMAZON = "amazon"
    REDDIT = "reddit"


class SourceKind(StrEnum):
    AMAZON_REVIEW = "amazon_review"
    REDDIT_THREAD = "reddit_thread"
    REDDIT_COMMENT = "reddit_comment"


class CollectionRunCreate(BaseModel):
    platform: Platform
    source_url: str
    capture_method: str
    coverage_scope: dict[str, Any] = Field(default_factory=dict)
    stop_reason: str | None = None
    coverage_confidence: float = Field(ge=0.0, le=1.0)


class CollectionRun(CollectionRunCreate):
    collection_run_id: str
    created_at: datetime


class RawSourceItem(BaseModel):
    platform: Platform
    source_kind: SourceKind
    source_object_id: str
    raw_schema_version: str
    parser_version: str
    raw_payload: dict[str, Any]
    raw_payload_hash: str
    captured_at: datetime


class CanonicalVocUnit(BaseModel):
    platform: Platform
    source_kind: SourceKind
    source_object_id: str
    collection_run_id: str
    source_url: str | HttpUrl
    captured_at: datetime
    created_at: datetime | None = None
    author_display: str | None = None
    author_type: str | None = None
    title: str | None = None
    body: str
    language: str | None = None
    media_refs: list[str] = Field(default_factory=list)
    commercial_object_type: str | None = None
    brand: str | None = None
    product_title: str | None = None
    asin: str | None = None
    parent_asin: str | None = None
    marketplace: str | None = None
    category: str | None = None
    thread_id: str | None = None
    parent_id: str | None = None
    depth: int | None = None
    reply_role: str | None = None
    quality_flags: list[str] = Field(default_factory=list)
    coverage_confidence: float = Field(ge=0.0, le=1.0)
    platform_extension: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
cd apps/api && uv run pytest tests/test_contracts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/plugin_hub_api/schemas.py apps/api/tests/test_contracts.py
git commit -m "锁定 VOC 数据契约"
```

## Task 3: Amazon ETL Mapping

**Files:**
- Create: `apps/api/src/plugin_hub_api/services/etl.py`
- Create: `apps/api/tests/test_etl_amazon.py`

- [ ] **Step 1: Write failing Amazon ETL tests**

Create `apps/api/tests/test_etl_amazon.py`:

```python
from datetime import UTC, datetime

from plugin_hub_api.schemas import Platform, SourceKind
from plugin_hub_api.services.etl import map_amazon_review_to_voc


def test_maps_amazon_review_to_canonical_voc_unit() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_001",
        source_url="https://www.amazon.com/product-reviews/B000000001?pageNumber=2",
        raw_review={
            "review_id": "R123",
            "rating": 2,
            "title": "Useful but breaks fast",
            "body": "The product worked for two weeks and then the switch stopped.",
            "asin": "B000000001",
            "parent_asin": "B000PARENT1",
            "marketplace": "US",
            "author": "Amazon Customer",
            "verified_purchase": True,
            "helpful_vote": 8,
            "review_page": 2,
            "sort_by": "recent",
            "filter_by_star": "critical",
            "captured_at": "2026-06-05T00:00:00+00:00",
        },
        coverage_confidence=0.82,
    )

    assert voc.platform == Platform.AMAZON
    assert voc.source_kind == SourceKind.AMAZON_REVIEW
    assert voc.source_object_id == "R123"
    assert voc.asin == "B000000001"
    assert voc.parent_asin == "B000PARENT1"
    assert voc.platform_extension["rating"] == 2
    assert voc.platform_extension["verified_purchase"] is True
    assert voc.quality_flags == []


def test_amazon_review_without_id_gets_quality_flag() -> None:
    voc = map_amazon_review_to_voc(
        collection_run_id="run_amz_002",
        source_url="https://www.amazon.com/product-reviews/B000000001",
        raw_review={
            "rating": 5,
            "body": "Good value.",
            "captured_at": datetime(2026, 6, 5, tzinfo=UTC).isoformat(),
        },
        coverage_confidence=0.45,
    )

    assert voc.source_object_id.startswith("amazon_missing_id_")
    assert "missing_review_id" in voc.quality_flags
    assert voc.coverage_confidence == 0.45
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd apps/api && uv run pytest tests/test_etl_amazon.py -v
```

Expected: FAIL with missing `plugin_hub_api.services.etl`.

- [ ] **Step 3: Implement Amazon ETL mapping**

Create `apps/api/src/plugin_hub_api/services/__init__.py`:

```python
"""Service modules for Plugin Hub API."""
```

Create `apps/api/src/plugin_hub_api/services/etl.py`:

```python
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from plugin_hub_api.schemas import CanonicalVocUnit, Platform, SourceKind


def _stable_missing_id(prefix: str, raw_payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(repr(sorted(raw_payload.items())).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None


def map_amazon_review_to_voc(
    *,
    collection_run_id: str,
    source_url: str,
    raw_review: dict[str, Any],
    coverage_confidence: float,
) -> CanonicalVocUnit:
    quality_flags: list[str] = []
    review_id = raw_review.get("review_id")
    if not review_id:
        review_id = _stable_missing_id("amazon_missing_id", raw_review)
        quality_flags.append("missing_review_id")

    captured_at = _parse_datetime(raw_review.get("captured_at")) or datetime.utcnow()
    body = str(raw_review.get("body") or raw_review.get("text") or "")
    if not body:
        quality_flags.append("missing_body")

    return CanonicalVocUnit(
        platform=Platform.AMAZON,
        source_kind=SourceKind.AMAZON_REVIEW,
        source_object_id=str(review_id),
        collection_run_id=collection_run_id,
        source_url=source_url,
        captured_at=captured_at,
        created_at=_parse_datetime(raw_review.get("created_at")),
        author_display=raw_review.get("author"),
        title=raw_review.get("title"),
        body=body,
        media_refs=list(raw_review.get("media_refs", [])),
        commercial_object_type="amazon_asin",
        asin=raw_review.get("asin"),
        parent_asin=raw_review.get("parent_asin"),
        marketplace=raw_review.get("marketplace"),
        quality_flags=quality_flags,
        coverage_confidence=coverage_confidence,
        platform_extension={
            "rating": raw_review.get("rating"),
            "verified_purchase": raw_review.get("verified_purchase"),
            "helpful_vote": raw_review.get("helpful_vote"),
            "review_page": raw_review.get("review_page"),
            "sort_by": raw_review.get("sort_by"),
            "filter_by_star": raw_review.get("filter_by_star"),
            "variant_context": raw_review.get("variant_context"),
        },
    )
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
cd apps/api && uv run pytest tests/test_etl_amazon.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/plugin_hub_api/services apps/api/tests/test_etl_amazon.py
git commit -m "实现 Amazon 评论 ETL 映射"
```

## Task 4: Reddit ETL Mapping

**Files:**
- Modify: `apps/api/src/plugin_hub_api/services/etl.py`
- Create: `apps/api/tests/test_etl_reddit.py`

- [ ] **Step 1: Write failing Reddit ETL tests**

Create `apps/api/tests/test_etl_reddit.py`:

```python
from plugin_hub_api.schemas import Platform, SourceKind
from plugin_hub_api.services.etl import map_reddit_comment_to_voc, map_reddit_thread_to_voc


def test_maps_reddit_thread_to_canonical_voc_unit() -> None:
    voc = map_reddit_thread_to_voc(
        collection_run_id="run_red_001",
        source_url="https://www.reddit.com/r/Coffee/comments/thread123/example/",
        raw_thread={
            "name": "t3_thread123",
            "id": "thread123",
            "subreddit": "Coffee",
            "title": "Best grinder for espresso?",
            "selftext": "I want a quieter grinder under $300.",
            "author": "buyer_researcher",
            "created_utc": 1780602718.0,
            "score": 42,
            "upvote_ratio": 0.88,
            "num_comments": 12,
            "locked": False,
            "archived": False,
            "link_flair_text": "Buying Advice",
        },
        coverage_confidence=0.95,
    )

    assert voc.platform == Platform.REDDIT
    assert voc.source_kind == SourceKind.REDDIT_THREAD
    assert voc.source_object_id == "t3_thread123"
    assert voc.thread_id == "t3_thread123"
    assert voc.platform_extension["subreddit"] == "Coffee"
    assert voc.platform_extension["upvote_ratio"] == 0.88


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
            "replies": "",
        },
        coverage_confidence=0.88,
    )

    assert voc.source_kind == SourceKind.REDDIT_COMMENT
    assert voc.thread_id == "t3_thread123"
    assert voc.parent_id == "t1_parent999"
    assert voc.depth == 2
    assert voc.reply_role == "nested_reply"


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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd apps/api && uv run pytest tests/test_etl_reddit.py -v
```

Expected: FAIL with missing Reddit mapper functions.

- [ ] **Step 3: Add Reddit ETL mapping**

Append to `apps/api/src/plugin_hub_api/services/etl.py`:

```python
from datetime import UTC


def _from_unix_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(float(value), tz=UTC)


def map_reddit_thread_to_voc(
    *,
    collection_run_id: str,
    source_url: str,
    raw_thread: dict[str, Any],
    coverage_confidence: float,
) -> CanonicalVocUnit:
    thread_id = str(raw_thread.get("name") or f"t3_{raw_thread['id']}")
    return CanonicalVocUnit(
        platform=Platform.REDDIT,
        source_kind=SourceKind.REDDIT_THREAD,
        source_object_id=thread_id,
        collection_run_id=collection_run_id,
        source_url=source_url,
        captured_at=datetime.utcnow(),
        created_at=_from_unix_utc(raw_thread.get("created_utc")),
        author_display=raw_thread.get("author"),
        title=raw_thread.get("title"),
        body=str(raw_thread.get("selftext") or ""),
        thread_id=thread_id,
        reply_role="thread_root",
        quality_flags=[],
        coverage_confidence=coverage_confidence,
        platform_extension={
            "subreddit": raw_thread.get("subreddit"),
            "post_flair": raw_thread.get("link_flair_text"),
            "score": raw_thread.get("score"),
            "upvote_ratio": raw_thread.get("upvote_ratio"),
            "num_comments": raw_thread.get("num_comments"),
            "locked": raw_thread.get("locked"),
            "archived": raw_thread.get("archived"),
        },
    )


def map_reddit_comment_to_voc(
    *,
    collection_run_id: str,
    source_url: str,
    thread_id: str,
    raw_comment: dict[str, Any],
    coverage_confidence: float,
) -> CanonicalVocUnit:
    quality_flags: list[str] = []
    is_more_node = raw_comment.get("kind") == "more"
    if is_more_node:
        quality_flags.append("reddit_more_node")
        source_object_id = f"more_{raw_comment.get('id')}"
        body = ""
    else:
        source_object_id = str(raw_comment.get("name") or f"t1_{raw_comment['id']}")
        body = str(raw_comment.get("body") or "")
        if raw_comment.get("body") in {"[deleted]", "[removed]"}:
            quality_flags.append("reddit_deleted_or_removed")

    parent_id = raw_comment.get("parent_id")
    depth = raw_comment.get("depth")
    reply_role = "top_level_reply" if parent_id == thread_id or depth == 0 else "nested_reply"

    return CanonicalVocUnit(
        platform=Platform.REDDIT,
        source_kind=SourceKind.REDDIT_COMMENT,
        source_object_id=source_object_id,
        collection_run_id=collection_run_id,
        source_url=source_url,
        captured_at=datetime.utcnow(),
        created_at=_from_unix_utc(raw_comment.get("created_utc")),
        author_display=raw_comment.get("author"),
        body=body,
        thread_id=thread_id,
        parent_id=parent_id,
        depth=depth,
        reply_role=reply_role,
        quality_flags=quality_flags,
        coverage_confidence=coverage_confidence,
        platform_extension={
            "score": raw_comment.get("score"),
            "is_submitter": raw_comment.get("is_submitter"),
            "link_id": raw_comment.get("link_id"),
            "more_node_count": len(raw_comment.get("children", [])) if is_more_node else 0,
        },
    )
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
cd apps/api && uv run pytest tests/test_etl_reddit.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/plugin_hub_api/services/etl.py apps/api/tests/test_etl_reddit.py
git commit -m "实现 Reddit 帖子与评论 ETL 映射"
```

## Task 5: Backend Persistence and Collection API

**Files:**
- Create: `apps/api/src/plugin_hub_api/config.py`
- Create: `apps/api/src/plugin_hub_api/db.py`
- Create: `apps/api/src/plugin_hub_api/models.py`
- Create: `apps/api/src/plugin_hub_api/repositories.py`
- Create: `apps/api/src/plugin_hub_api/main.py`
- Create: `apps/api/src/plugin_hub_api/routes/__init__.py`
- Create: `apps/api/src/plugin_hub_api/routes/collection_runs.py`
- Create: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_collection_runs_api.py`

- [ ] **Step 1: Write failing API tests**

Create `apps/api/tests/conftest.py`:

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from plugin_hub_api.main import create_app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = create_app(database_url="sqlite+pysqlite:///:memory:")
    with TestClient(app) as test_client:
        yield test_client
```

Create `apps/api/tests/test_collection_runs_api.py`:

```python
from fastapi.testclient import TestClient


def test_create_collection_run_with_amazon_raw_item(client: TestClient) -> None:
    response = client.post(
        "/api/collection-runs",
        json={
            "run": {
                "platform": "amazon",
                "source_url": "https://www.amazon.com/product-reviews/B000000001",
                "capture_method": "extension_dom",
                "coverage_scope": {"segment": "recent_all"},
                "stop_reason": "max_pages_reached",
                "coverage_confidence": 0.8,
            },
            "raw_items": [
                {
                    "platform": "amazon",
                    "source_kind": "amazon_review",
                    "source_object_id": "R123",
                    "raw_schema_version": "raw_amazon_review_v1",
                    "parser_version": "amazon-dom-parser@0.1.0",
                    "raw_payload": {
                        "review_id": "R123",
                        "rating": 1,
                        "title": "Bad switch",
                        "body": "The switch broke.",
                        "captured_at": "2026-06-05T00:00:00+00:00"
                    },
                    "raw_payload_hash": "hash123",
                    "captured_at": "2026-06-05T00:00:00+00:00"
                }
            ]
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["collection_run_id"].startswith("run_")
    assert body["raw_item_count"] == 1
    assert body["voc_unit_count"] == 1


def test_list_voc_units_returns_created_units(client: TestClient) -> None:
    client.post(
        "/api/collection-runs",
        json={
            "run": {
                "platform": "reddit",
                "source_url": "https://www.reddit.com/r/Coffee/comments/thread123/example/",
                "capture_method": "reddit_json",
                "coverage_scope": {"thread_id": "t3_thread123"},
                "stop_reason": "json_complete",
                "coverage_confidence": 0.9,
            },
            "raw_items": [
                {
                    "platform": "reddit",
                    "source_kind": "reddit_thread",
                    "source_object_id": "t3_thread123",
                    "raw_schema_version": "raw_reddit_thread_v1",
                    "parser_version": "reddit-json-parser@0.1.0",
                    "raw_payload": {
                        "name": "t3_thread123",
                        "id": "thread123",
                        "title": "Quiet grinder?",
                        "selftext": "Need a quiet grinder.",
                        "created_utc": 1780602718.0
                    },
                    "raw_payload_hash": "hash456",
                    "captured_at": "2026-06-05T00:00:00+00:00"
                }
            ]
        },
    )

    response = client.get("/api/voc-units?platform=reddit")

    assert response.status_code == 200
    assert response.json()["items"][0]["thread_id"] == "t3_thread123"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd apps/api && uv run pytest tests/test_collection_runs_api.py -v
```

Expected: FAIL with missing `plugin_hub_api.main`.

- [ ] **Step 3: Implement API and in-memory test persistence**
- [ ] **Step 3: Implement API with SQLAlchemy persistence**

Create `apps/api/src/plugin_hub_api/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+pysqlite:///:memory:"
```

Create `apps/api/src/plugin_hub_api/db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> Engine:
    if database_url == "sqlite+pysqlite:///:memory:":
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    from plugin_hub_api import models

    Base.metadata.create_all(engine)
```

Create `apps/api/src/plugin_hub_api/models.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from plugin_hub_api.db import Base


class CollectionRunModel(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    capture_method: Mapped[str] = mapped_column(String(64))
    coverage_scope: Mapped[dict[str, Any]] = mapped_column(JSON)
    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    coverage_confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RawSourceItemModel(Base):
    __tablename__ = "raw_source_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("collection_runs.collection_run_id"),
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(32), index=True)
    source_kind: Mapped[str] = mapped_column(String(64), index=True)
    source_object_id: Mapped[str] = mapped_column(String(128), index=True)
    raw_schema_version: Mapped[str] = mapped_column(String(64))
    parser_version: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    raw_payload_hash: Mapped[str] = mapped_column(String(128), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CanonicalVocUnitModel(Base):
    __tablename__ = "canonical_voc_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voc_unit_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    source_kind: Mapped[str] = mapped_column(String(64), index=True)
    source_object_id: Mapped[str] = mapped_column(String(128), index=True)
    collection_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("collection_runs.collection_run_id"),
        index=True,
    )
    source_url: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    author_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    media_refs: Mapped[list[str]] = mapped_column(JSON)
    commercial_object_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    asin: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    parent_asin: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    marketplace: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reply_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality_flags: Mapped[list[str]] = mapped_column(JSON)
    coverage_confidence: Mapped[float] = mapped_column(Float)
    platform_extension: Mapped[dict[str, Any]] = mapped_column(JSON)
```

Create `apps/api/src/plugin_hub_api/repositories.py`:

```python
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from plugin_hub_api.models import CanonicalVocUnitModel, CollectionRunModel, RawSourceItemModel
from plugin_hub_api.schemas import CanonicalVocUnit, CollectionRun, Platform, RawSourceItem, SourceKind


class SqlAlchemyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_collection(
        self,
        *,
        run: CollectionRun,
        raw_items: list[RawSourceItem],
        voc_units: list[CanonicalVocUnit],
    ) -> None:
        self.session.add(
            CollectionRunModel(
                collection_run_id=run.collection_run_id,
                platform=run.platform.value,
                source_url=run.source_url,
                capture_method=run.capture_method,
                coverage_scope=run.coverage_scope,
                stop_reason=run.stop_reason,
                coverage_confidence=run.coverage_confidence,
                created_at=run.created_at,
            )
        )

        self.session.add_all(
            RawSourceItemModel(
                collection_run_id=run.collection_run_id,
                platform=item.platform.value,
                source_kind=item.source_kind.value,
                source_object_id=item.source_object_id,
                raw_schema_version=item.raw_schema_version,
                parser_version=item.parser_version,
                raw_payload=item.raw_payload,
                raw_payload_hash=item.raw_payload_hash,
                captured_at=item.captured_at,
            )
            for item in raw_items
        )

        self.session.add_all(
            CanonicalVocUnitModel(
                voc_unit_id=f"voc_{uuid4().hex[:16]}",
                platform=unit.platform.value,
                source_kind=unit.source_kind.value,
                source_object_id=unit.source_object_id,
                collection_run_id=unit.collection_run_id,
                source_url=str(unit.source_url),
                captured_at=unit.captured_at,
                created_at=unit.created_at,
                author_display=unit.author_display,
                author_type=unit.author_type,
                title=unit.title,
                body=unit.body,
                language=unit.language,
                media_refs=unit.media_refs,
                commercial_object_type=unit.commercial_object_type,
                brand=unit.brand,
                product_title=unit.product_title,
                asin=unit.asin,
                parent_asin=unit.parent_asin,
                marketplace=unit.marketplace,
                category=unit.category,
                thread_id=unit.thread_id,
                parent_id=unit.parent_id,
                depth=unit.depth,
                reply_role=unit.reply_role,
                quality_flags=unit.quality_flags,
                coverage_confidence=unit.coverage_confidence,
                platform_extension=unit.platform_extension,
            )
            for unit in voc_units
        )

        self.session.commit()

    def list_voc_units(self, platform: Platform | None = None) -> list[CanonicalVocUnit]:
        statement = select(CanonicalVocUnitModel)
        if platform is not None:
            statement = statement.where(CanonicalVocUnitModel.platform == platform.value)

        rows = self.session.execute(statement).scalars().all()
        return [
            CanonicalVocUnit(
                platform=Platform(row.platform),
                source_kind=SourceKind(row.source_kind),
                source_object_id=row.source_object_id,
                collection_run_id=row.collection_run_id,
                source_url=row.source_url,
                captured_at=row.captured_at,
                created_at=row.created_at,
                author_display=row.author_display,
                author_type=row.author_type,
                title=row.title,
                body=row.body,
                language=row.language,
                media_refs=row.media_refs,
                commercial_object_type=row.commercial_object_type,
                brand=row.brand,
                product_title=row.product_title,
                asin=row.asin,
                parent_asin=row.parent_asin,
                marketplace=row.marketplace,
                category=row.category,
                thread_id=row.thread_id,
                parent_id=row.parent_id,
                depth=row.depth,
                reply_role=row.reply_role,
                quality_flags=row.quality_flags,
                coverage_confidence=row.coverage_confidence,
                platform_extension=row.platform_extension,
            )
            for row in rows
        ]
```

Create `apps/api/src/plugin_hub_api/routes/collection_runs.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.schemas import CollectionRun, CollectionRunCreate, Platform, RawSourceItem, SourceKind
from plugin_hub_api.services.etl import (
    map_amazon_review_to_voc,
    map_reddit_comment_to_voc,
    map_reddit_thread_to_voc,
)

router = APIRouter()


class CollectionRunPayload(BaseModel):
    run: CollectionRunCreate
    raw_items: list[RawSourceItem]


class CollectionRunResponse(BaseModel):
    collection_run_id: str
    raw_item_count: int
    voc_unit_count: int


class VocUnitListResponse(BaseModel):
    items: list[dict]


def get_repository() -> SqlAlchemyRepository:
    raise RuntimeError("Repository dependency is not configured")


@router.post("/collection-runs", response_model=CollectionRunResponse, status_code=status.HTTP_201_CREATED)
def create_collection_run(
    payload: CollectionRunPayload,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
) -> CollectionRunResponse:
    run_id = f"run_{uuid4().hex[:12]}"
    run = CollectionRun(
        **payload.run.model_dump(),
        collection_run_id=run_id,
        created_at=datetime.now(tz=UTC),
    )
    voc_units = []

    for raw_item in payload.raw_items:
        if raw_item.source_kind == SourceKind.AMAZON_REVIEW:
            voc_units.append(
                map_amazon_review_to_voc(
                    collection_run_id=run_id,
                    source_url=payload.run.source_url,
                    raw_review=raw_item.raw_payload,
                    coverage_confidence=payload.run.coverage_confidence,
                )
            )
        elif raw_item.source_kind == SourceKind.REDDIT_THREAD:
            voc_units.append(
                map_reddit_thread_to_voc(
                    collection_run_id=run_id,
                    source_url=payload.run.source_url,
                    raw_thread=raw_item.raw_payload,
                    coverage_confidence=payload.run.coverage_confidence,
                )
            )
        elif raw_item.source_kind == SourceKind.REDDIT_COMMENT:
            voc_units.append(
                map_reddit_comment_to_voc(
                    collection_run_id=run_id,
                    source_url=payload.run.source_url,
                    thread_id=str(raw_item.raw_payload.get("link_id") or raw_item.raw_payload.get("thread_id")),
                    raw_comment=raw_item.raw_payload,
                    coverage_confidence=payload.run.coverage_confidence,
                )
            )

    repository.save_collection(run=run, raw_items=payload.raw_items, voc_units=voc_units)

    return CollectionRunResponse(
        collection_run_id=run_id,
        raw_item_count=len(payload.raw_items),
        voc_unit_count=len(voc_units),
    )


@router.get("/voc-units", response_model=VocUnitListResponse)
def list_voc_units(
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    platform: Platform | None = None,
) -> VocUnitListResponse:
    items = [unit.model_dump(mode="json") for unit in repository.list_voc_units(platform)]
    return VocUnitListResponse(items=items)
```

Create `apps/api/src/plugin_hub_api/main.py`:

```python
from collections.abc import Generator

from fastapi import Depends
from fastapi import FastAPI
from sqlalchemy.orm import Session

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes import collection_runs


def create_app(*, database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="Plugin Hub API")
    settings = Settings()
    engine = build_engine(database_url or settings.database_url)
    init_database(engine)
    session_factory = make_session_factory(engine)

    def get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    def repository_override(session: Session = Depends(get_session)) -> SqlAlchemyRepository:
        return SqlAlchemyRepository(session)

    app.dependency_overrides[collection_runs.get_repository] = repository_override
    app.include_router(collection_runs.router, prefix="/api")
    return app


app = create_app()
```

Create `apps/api/src/plugin_hub_api/routes/__init__.py`:

```python
"""API route package."""
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
cd apps/api && uv run pytest tests/test_collection_runs_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/plugin_hub_api apps/api/tests/conftest.py apps/api/tests/test_collection_runs_api.py
git commit -m "实现 VOC 采集回传 API"
```

## Task 6: Insight Template Service

**Files:**
- Create: `apps/api/src/plugin_hub_api/services/insights.py`
- Create: `apps/api/src/plugin_hub_api/routes/insights.py`
- Modify: `apps/api/src/plugin_hub_api/main.py`
- Create: `apps/api/tests/test_insights.py`

- [ ] **Step 1: Write failing insight tests**

Create `apps/api/tests/test_insights.py`:

```python
from plugin_hub_api.schemas import CanonicalVocUnit, Platform, SourceKind
from plugin_hub_api.services.insights import generate_strategy_notes


def test_generate_strategy_notes_groups_pain_points() -> None:
    units = [
        CanonicalVocUnit(
            platform=Platform.AMAZON,
            source_kind=SourceKind.AMAZON_REVIEW,
            source_object_id="R1",
            collection_run_id="run_1",
            source_url="https://amazon.example/review/R1",
            captured_at="2026-06-05T00:00:00+00:00",
            title="Too loud",
            body="The motor is too loud for a small apartment.",
            quality_flags=[],
            coverage_confidence=0.9,
            platform_extension={"rating": 2},
        ),
        CanonicalVocUnit(
            platform=Platform.REDDIT,
            source_kind=SourceKind.REDDIT_COMMENT,
            source_object_id="t1_abc",
            collection_run_id="run_2",
            source_url="https://reddit.example/comment",
            captured_at="2026-06-05T00:00:00+00:00",
            body="Noise is the deal breaker.",
            thread_id="t3_thread",
            quality_flags=[],
            coverage_confidence=0.8,
        ),
    ]

    notes = generate_strategy_notes(units)

    assert notes[0]["strategy_type"] == "product_or_listing"
    assert notes[0]["topic"] == "noise"
    assert notes[0]["evidence_count"] == 2
    assert "motor is too loud" in notes[0]["evidence_examples"][0]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd apps/api && uv run pytest tests/test_insights.py -v
```

Expected: FAIL with missing `services.insights`.

- [ ] **Step 3: Implement deterministic insight service**

Create `apps/api/src/plugin_hub_api/services/insights.py`:

```python
from __future__ import annotations

from plugin_hub_api.schemas import CanonicalVocUnit


def _topic_for_text(text: str) -> str:
    lowered = text.lower()
    if "noise" in lowered or "loud" in lowered:
        return "noise"
    if "break" in lowered or "broken" in lowered or "stopped" in lowered:
        return "durability"
    if "price" in lowered or "expensive" in lowered:
        return "price"
    return "general"


def generate_strategy_notes(units: list[CanonicalVocUnit]) -> list[dict]:
    grouped: dict[str, list[CanonicalVocUnit]] = {}
    for unit in units:
        topic = _topic_for_text(f"{unit.title or ''} {unit.body}")
        grouped.setdefault(topic, []).append(unit)

    notes = []
    for topic, topic_units in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True):
        notes.append(
            {
                "strategy_type": "product_or_listing",
                "topic": topic,
                "evidence_count": len(topic_units),
                "evidence_examples": [unit.body for unit in topic_units[:3]],
                "recommendation": f"Review {topic} language before changing listing, product, or ad copy.",
                "evidence_strength": min(unit.coverage_confidence for unit in topic_units),
            }
        )
    return notes
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
cd apps/api && uv run pytest tests/test_insights.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/plugin_hub_api/services/insights.py apps/api/tests/test_insights.py
git commit -m "实现可追溯策略洞察模板"
```

## Task 7: Extension Project and Shared Contracts

**Files:**
- Create: `apps/extension/package.json`
- Create: `apps/extension/tsconfig.json`
- Create: `apps/extension/vite.config.ts`
- Create: `apps/extension/manifest.config.ts`
- Create: `apps/extension/src/types/contracts.ts`
- Create: `apps/extension/tests/page-detect.test.ts`
- Create: `apps/extension/src/lib/page-detect.ts`

- [ ] **Step 1: Create extension package**

Create `apps/extension/package.json`:

```json
{
  "name": "@plugin-hub/extension",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest run",
    "lint": "eslint src tests --ext .ts,.tsx",
    "typecheck": "tsc --noEmit",
    "build": "vite build"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.7",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "vitest": "^2.1.8",
    "jsdom": "^25.0.1",
    "@types/chrome": "^0.0.287",
    "@types/react": "^19.0.2",
    "@types/react-dom": "^19.0.2"
  }
}
```

Create `apps/extension/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "react-jsx",
    "types": ["chrome", "vitest/globals"],
    "skipLibCheck": true
  },
  "include": ["src", "tests", "vite.config.ts", "manifest.config.ts"]
}
```

Create `apps/extension/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom"
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
```

- [ ] **Step 2: Create shared contract types**

Create `apps/extension/src/types/contracts.ts`:

```ts
export type Platform = "amazon" | "reddit";
export type SourceKind = "amazon_review" | "reddit_thread" | "reddit_comment";

export interface RawSourceItem {
  platform: Platform;
  source_kind: SourceKind;
  source_object_id: string;
  raw_schema_version: string;
  parser_version: string;
  raw_payload: Record<string, unknown>;
  raw_payload_hash: string;
  captured_at: string;
}

export interface CollectionRunPayload {
  run: {
    platform: Platform;
    source_url: string;
    capture_method: string;
    coverage_scope: Record<string, unknown>;
    stop_reason: string | null;
    coverage_confidence: number;
  };
  raw_items: RawSourceItem[];
}
```

- [ ] **Step 3: Write failing page detection tests**

Create `apps/extension/tests/page-detect.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { detectPage } from "../src/lib/page-detect";

describe("detectPage", () => {
  it("detects Amazon review pages", () => {
    const result = detectPage("https://www.amazon.com/product-reviews/B000000001?pageNumber=2");

    expect(result).toEqual({ platform: "amazon", pageKind: "amazon_reviews", asin: "B000000001" });
  });

  it("detects Reddit thread pages", () => {
    const result = detectPage("https://www.reddit.com/r/Coffee/comments/thread123/example/");

    expect(result).toEqual({ platform: "reddit", pageKind: "reddit_thread", threadId: "thread123" });
  });
});
```

- [ ] **Step 4: Run tests and verify failure**

Run:

```bash
pnpm --filter @plugin-hub/extension test
```

Expected: FAIL with missing `src/lib/page-detect`.

- [ ] **Step 5: Implement page detection**

Create `apps/extension/src/lib/page-detect.ts`:

```ts
export type DetectedPage =
  | { platform: "amazon"; pageKind: "amazon_reviews"; asin: string }
  | { platform: "reddit"; pageKind: "reddit_thread"; threadId: string }
  | { platform: "unknown"; pageKind: "unknown" };

export function detectPage(url: string): DetectedPage {
  const parsed = new URL(url);
  const amazonMatch = parsed.pathname.match(/\/product-reviews\/([A-Z0-9]{10})/);
  if (parsed.hostname.includes("amazon.") && amazonMatch) {
    return { platform: "amazon", pageKind: "amazon_reviews", asin: amazonMatch[1] };
  }

  const redditMatch = parsed.pathname.match(/\/r\/[^/]+\/comments\/([^/]+)/);
  if (parsed.hostname.includes("reddit.com") && redditMatch) {
    return { platform: "reddit", pageKind: "reddit_thread", threadId: redditMatch[1] };
  }

  return { platform: "unknown", pageKind: "unknown" };
}
```

- [ ] **Step 6: Run tests and verify pass**

Run:

```bash
pnpm --filter @plugin-hub/extension test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/extension package.json pnpm-lock.yaml
git commit -m "搭建 Chrome 插件采集工程"
```

## Task 8: Amazon Parser and Pagination State

**Files:**
- Create: `apps/extension/src/lib/amazon-parser.ts`
- Create: `apps/extension/tests/amazon-parser.test.ts`

- [ ] **Step 1: Write failing Amazon parser tests**

Create `apps/extension/tests/amazon-parser.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseAmazonReviews } from "../src/lib/amazon-parser";

describe("parseAmazonReviews", () => {
  it("extracts review fields and pagination context", () => {
    document.body.innerHTML = `
      <div data-hook="review" id="R123">
        <i data-hook="review-star-rating"><span>2.0 out of 5 stars</span></i>
        <a data-hook="review-title"><span>Breaks fast</span></a>
        <span data-hook="review-body"><span>The switch broke after two weeks.</span></span>
        <span data-hook="avp-badge">Verified Purchase</span>
        <span data-hook="helpful-vote-statement">8 people found this helpful</span>
      </div>
      <li class="a-selected"><a>2</a></li>
      <li class="a-last"><a href="/product-reviews/B000000001?pageNumber=3">Next</a></li>
    `;

    const result = parseAmazonReviews({
      asin: "B000000001",
      marketplace: "US",
      sourceUrl: "https://www.amazon.com/product-reviews/B000000001?pageNumber=2",
      segment: "critical_1_2_star"
    });

    expect(result.rawItems[0].source_object_id).toBe("R123");
    expect(result.rawItems[0].raw_payload).toMatchObject({
      rating: 2,
      title: "Breaks fast",
      verified_purchase: true,
      helpful_vote: 8,
      review_page: 2
    });
    expect(result.stopReason).toBeNull();
    expect(result.nextPageUrl).toContain("pageNumber=3");
  });
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pnpm --filter @plugin-hub/extension test amazon-parser.test.ts
```

Expected: FAIL with missing `amazon-parser`.

- [ ] **Step 3: Implement Amazon parser**

Create `apps/extension/src/lib/amazon-parser.ts`:

```ts
import type { RawSourceItem } from "../types/contracts";

interface AmazonParseInput {
  asin: string;
  marketplace: string;
  sourceUrl: string;
  segment: string;
}

interface AmazonParseResult {
  rawItems: RawSourceItem[];
  stopReason: string | null;
  nextPageUrl: string | null;
}

function text(selector: string, root: ParentNode = document): string {
  return root.querySelector(selector)?.textContent?.trim() ?? "";
}

function parseRating(value: string): number | null {
  const match = value.match(/([0-5](?:\.\d)?)\s+out of 5/);
  return match ? Number(match[1]) : null;
}

function parseHelpful(value: string): number | null {
  const match = value.match(/(\d+)/);
  return match ? Number(match[1]) : null;
}

function hashPayload(payload: Record<string, unknown>): string {
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload)))).slice(0, 24);
}

export function parseAmazonReviews(input: AmazonParseInput): AmazonParseResult {
  const reviews = Array.from(document.querySelectorAll<HTMLElement>('[data-hook="review"]'));
  const observedPage = Number(text(".a-selected a")) || null;
  const nextHref = document.querySelector<HTMLAnchorElement>("li.a-last a")?.href ?? null;
  const capturedAt = new Date().toISOString();

  const rawItems = reviews.map((review, index): RawSourceItem => {
    const reviewId = review.id || `missing_review_${index}`;
    const rawPayload = {
      review_id: reviewId,
      rating: parseRating(text('[data-hook="review-star-rating"] span', review)),
      title: text('[data-hook="review-title"] span', review),
      body: text('[data-hook="review-body"] span', review),
      asin: input.asin,
      marketplace: input.marketplace,
      verified_purchase: text('[data-hook="avp-badge"]', review).length > 0,
      helpful_vote: parseHelpful(text('[data-hook="helpful-vote-statement"]', review)),
      review_page: observedPage,
      filter_by_star: input.segment,
      captured_at: capturedAt
    };

    return {
      platform: "amazon",
      source_kind: "amazon_review",
      source_object_id: reviewId,
      raw_schema_version: "raw_amazon_review_v1",
      parser_version: "amazon-dom-parser@0.1.0",
      raw_payload: rawPayload,
      raw_payload_hash: hashPayload(rawPayload),
      captured_at: capturedAt
    };
  });

  return {
    rawItems,
    stopReason: reviews.length === 0 ? "empty_dom" : null,
    nextPageUrl: nextHref
  };
}
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pnpm --filter @plugin-hub/extension test amazon-parser.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/extension/src/lib/amazon-parser.ts apps/extension/tests/amazon-parser.test.ts
git commit -m "实现 Amazon 评论页面解析"
```

## Task 9: Reddit JSON Parser

**Files:**
- Create: `apps/extension/src/lib/reddit-parser.ts`
- Create: `apps/extension/tests/reddit-parser.test.ts`

- [ ] **Step 1: Write failing Reddit parser tests**

Create `apps/extension/tests/reddit-parser.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseRedditThreadJson } from "../src/lib/reddit-parser";

describe("parseRedditThreadJson", () => {
  it("extracts thread, comments, and more nodes", () => {
    const result = parseRedditThreadJson(
      [
        {
          kind: "Listing",
          data: {
            children: [
              {
                kind: "t3",
                data: {
                  name: "t3_thread123",
                  id: "thread123",
                  title: "Quiet grinder?",
                  selftext: "Need a quiet grinder.",
                  subreddit: "Coffee",
                  created_utc: 1780602718
                }
              }
            ]
          }
        },
        {
          kind: "Listing",
          data: {
            children: [
              {
                kind: "t1",
                data: {
                  name: "t1_comment456",
                  id: "comment456",
                  body: "Noise is the real issue.",
                  parent_id: "t3_thread123",
                  link_id: "t3_thread123",
                  depth: 0,
                  replies: ""
                }
              },
              {
                kind: "more",
                data: {
                  id: "more789",
                  parent_id: "t1_comment456",
                  children: ["abc", "def"],
                  depth: 1
                }
              }
            ]
          }
        }
      ],
      "https://www.reddit.com/r/Coffee/comments/thread123/example/"
    );

    expect(result.rawItems).toHaveLength(3);
    expect(result.rawItems[0].source_kind).toBe("reddit_thread");
    expect(result.rawItems[1].source_object_id).toBe("t1_comment456");
    expect(result.moreNodeCount).toBe(1);
  });
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pnpm --filter @plugin-hub/extension test reddit-parser.test.ts
```

Expected: FAIL with missing `reddit-parser`.

- [ ] **Step 3: Implement Reddit parser**

Create `apps/extension/src/lib/reddit-parser.ts`:

```ts
import type { RawSourceItem } from "../types/contracts";

interface RedditParseResult {
  rawItems: RawSourceItem[];
  moreNodeCount: number;
}

function hashPayload(payload: Record<string, unknown>): string {
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload)))).slice(0, 24);
}

function rawItem(kind: "reddit_thread" | "reddit_comment", sourceObjectId: string, payload: Record<string, unknown>): RawSourceItem {
  const capturedAt = new Date().toISOString();
  return {
    platform: "reddit",
    source_kind: kind,
    source_object_id: sourceObjectId,
    raw_schema_version: kind === "reddit_thread" ? "raw_reddit_thread_v1" : "raw_reddit_comment_v1",
    parser_version: "reddit-json-parser@0.1.0",
    raw_payload: payload,
    raw_payload_hash: hashPayload(payload),
    captured_at: capturedAt
  };
}

function walkComments(children: Array<Record<string, unknown>>, output: RawSourceItem[]): number {
  let moreCount = 0;
  for (const child of children) {
    const kind = child.kind as string;
    const data = child.data as Record<string, unknown>;
    if (kind === "t1") {
      const sourceId = String(data.name ?? `t1_${data.id}`);
      output.push(rawItem("reddit_comment", sourceId, data));
      const replies = data.replies as { data?: { children?: Array<Record<string, unknown>> } } | "";
      if (typeof replies === "object" && replies.data?.children) {
        moreCount += walkComments(replies.data.children, output);
      }
    }
    if (kind === "more") {
      moreCount += 1;
      output.push(rawItem("reddit_comment", `more_${data.id}`, { ...data, kind: "more" }));
    }
  }
  return moreCount;
}

export function parseRedditThreadJson(payload: unknown, sourceUrl: string): RedditParseResult {
  const listings = payload as Array<{ data: { children: Array<Record<string, unknown>> } }>;
  const rawItems: RawSourceItem[] = [];
  const thread = listings[0]?.data.children[0] as { kind: string; data: Record<string, unknown> } | undefined;
  if (thread?.kind === "t3") {
    rawItems.push(rawItem("reddit_thread", String(thread.data.name ?? `t3_${thread.data.id}`), thread.data));
  }
  const commentChildren = listings[1]?.data.children ?? [];
  const moreNodeCount = walkComments(commentChildren, rawItems);
  return { rawItems, moreNodeCount };
}
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pnpm --filter @plugin-hub/extension test reddit-parser.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/extension/src/lib/reddit-parser.ts apps/extension/tests/reddit-parser.test.ts
git commit -m "实现 Reddit JSON 结构解析"
```

## Task 10: Extension Upload Flow

**Files:**
- Create: `apps/extension/src/lib/upload-client.ts`
- Create: `apps/extension/src/background/service-worker.ts`
- Create: `apps/extension/src/content/content-script.ts`
- Create: `apps/extension/src/popup/Popup.tsx`
- Modify: `apps/extension/manifest.config.ts`
- Create: `apps/extension/tests/upload-client.test.ts`

- [ ] **Step 1: Write failing upload client test**

Create `apps/extension/tests/upload-client.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { uploadCollectionRun } from "../src/lib/upload-client";

describe("uploadCollectionRun", () => {
  it("posts collection payload to private backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ collection_run_id: "run_123", raw_item_count: 1, voc_unit_count: 1 })
    });

    const result = await uploadCollectionRun(
      "http://localhost:8000",
      {
        run: {
          platform: "amazon",
          source_url: "https://amazon.example",
          capture_method: "extension_dom",
          coverage_scope: { segment: "recent_all" },
          stop_reason: "max_pages_reached",
          coverage_confidence: 0.8
        },
        raw_items: []
      },
      fetchMock
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/collection-runs",
      expect.objectContaining({ method: "POST" })
    );
    expect(result.collection_run_id).toBe("run_123");
  });
});
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pnpm --filter @plugin-hub/extension test upload-client.test.ts
```

Expected: FAIL with missing `upload-client`.

- [ ] **Step 3: Implement upload client**

Create `apps/extension/src/lib/upload-client.ts`:

```ts
import type { CollectionRunPayload } from "../types/contracts";

interface UploadResponse {
  collection_run_id: string;
  raw_item_count: number;
  voc_unit_count: number;
}

export async function uploadCollectionRun(
  apiBaseUrl: string,
  payload: CollectionRunPayload,
  fetcher: typeof fetch = fetch
): Promise<UploadResponse> {
  const response = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/api/collection-runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`collection_run_upload_failed:${response.status}`);
  }

  return response.json() as Promise<UploadResponse>;
}
```

- [ ] **Step 4: Create MV3 shell files**

Create `apps/extension/src/background/service-worker.ts`:

```ts
import { uploadCollectionRun } from "../lib/upload-client";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "PLUGIN_HUB_UPLOAD_COLLECTION") {
    return false;
  }

  uploadCollectionRun(message.apiBaseUrl, message.payload)
    .then(sendResponse)
    .catch((error: Error) => sendResponse({ error: error.message }));
  return true;
});
```

Create `apps/extension/src/content/content-script.ts`:

```ts
import { detectPage } from "../lib/page-detect";

const detected = detectPage(window.location.href);
window.dispatchEvent(new CustomEvent("plugin-hub-page-detected", { detail: detected }));
```

Create `apps/extension/src/popup/Popup.tsx`:

```tsx
export function Popup() {
  return (
    <main>
      <h1>Plugin Hub</h1>
      <button type="button">Capture VOC</button>
    </main>
  );
}
```

Create `apps/extension/manifest.config.ts`:

```ts
export default {
  manifest_version: 3,
  name: "Plugin Hub VOC Capture",
  version: "0.1.0",
  permissions: ["activeTab", "storage"],
  host_permissions: [
    "https://*.amazon.com/*",
    "https://*.reddit.com/*",
    "http://localhost:8000/*"
  ],
  background: {
    service_worker: "src/background/service-worker.ts",
    type: "module"
  },
  content_scripts: [
    {
      matches: ["https://*.amazon.com/*", "https://*.reddit.com/*"],
      js: ["src/content/content-script.ts"]
    }
  ],
  action: {
    default_title: "Plugin Hub"
  }
};
```

- [ ] **Step 5: Run tests and typecheck**

Run:

```bash
pnpm --filter @plugin-hub/extension test
pnpm --filter @plugin-hub/extension typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/extension/src apps/extension/manifest.config.ts apps/extension/tests/upload-client.test.ts
git commit -m "实现插件采集回传通道"
```

## Task 11: VOC Hub Web App

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/app/globals.css`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/components/VocEvidenceTable.tsx`
- Create: `apps/web/src/components/QualityBadge.tsx`
- Create: `apps/web/tests/api.test.ts`

- [ ] **Step 1: Create web package**

Create `apps/web/package.json`:

```json
{
  "name": "@plugin-hub/web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "test": "vitest run",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^15.1.4",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@types/node": "^22.10.5",
    "@types/react": "^19.0.2",
    "@types/react-dom": "^19.0.2",
    "vitest": "^2.1.8"
  }
}
```

Create `apps/web/next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
```

Create `apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 2: Write failing API client test**

Create `apps/web/tests/api.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { fetchVocUnits } from "../src/lib/api";

describe("fetchVocUnits", () => {
  it("fetches VOC units by platform", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [{ source_object_id: "R123", platform: "amazon" }] })
    });

    const result = await fetchVocUnits("http://localhost:8000", "amazon", fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/voc-units?platform=amazon");
    expect(result.items[0].source_object_id).toBe("R123");
  });
});
```

- [ ] **Step 3: Run test and verify failure**

Run:

```bash
pnpm --filter @plugin-hub/web test api.test.ts
```

Expected: FAIL with missing `src/lib/api`.

- [ ] **Step 4: Implement web API client and page**

Create `apps/web/src/lib/api.ts`:

```ts
export interface VocUnit {
  source_object_id: string;
  platform: "amazon" | "reddit";
  title?: string | null;
  body: string;
  quality_flags: string[];
  coverage_confidence: number;
  platform_extension: Record<string, unknown>;
}

export interface VocUnitResponse {
  items: VocUnit[];
}

export async function fetchVocUnits(
  apiBaseUrl: string,
  platform: "amazon" | "reddit" | "all",
  fetcher: typeof fetch = fetch
): Promise<VocUnitResponse> {
  const query = platform === "all" ? "" : `?platform=${platform}`;
  const response = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/api/voc-units${query}`);
  if (!response.ok) {
    throw new Error(`voc_units_fetch_failed:${response.status}`);
  }
  return response.json() as Promise<VocUnitResponse>;
}
```

Create `apps/web/src/components/QualityBadge.tsx`:

```tsx
export function QualityBadge({ confidence }: { confidence: number }) {
  const label = confidence >= 0.8 ? "High" : confidence >= 0.5 ? "Medium" : "Low";
  return <span aria-label={`coverage confidence ${label}`}>{label}</span>;
}
```

Create `apps/web/src/components/VocEvidenceTable.tsx`:

```tsx
import type { VocUnit } from "../lib/api";
import { QualityBadge } from "./QualityBadge";

export function VocEvidenceTable({ items }: { items: VocUnit[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Platform</th>
          <th>Evidence</th>
          <th>Quality</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.source_object_id}>
            <td>{item.platform}</td>
            <td>{item.title ? `${item.title}: ${item.body}` : item.body}</td>
            <td><QualityBadge confidence={item.coverage_confidence} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

Create `apps/web/app/layout.tsx`:

```tsx
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
```

Create `apps/web/app/page.tsx`:

```tsx
import { VocEvidenceTable } from "../src/components/VocEvidenceTable";
import { fetchVocUnits } from "../src/lib/api";

export default async function Page() {
  const apiBaseUrl = process.env.PLUGIN_HUB_API_URL ?? "http://localhost:8000";
  const data = await fetchVocUnits(apiBaseUrl, "all");

  return (
    <main>
      <h1>VOC Hub</h1>
      <VocEvidenceTable items={data.items} />
    </main>
  );
}
```

Create `apps/web/app/globals.css`:

```css
body {
  font-family: Arial, sans-serif;
  margin: 0;
  color: #111827;
  background: #f8fafc;
}

main {
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

th,
td {
  border-bottom: 1px solid #e5e7eb;
  padding: 12px;
  text-align: left;
}
```

- [ ] **Step 5: Run tests and typecheck**

Run:

```bash
pnpm --filter @plugin-hub/web test
pnpm --filter @plugin-hub/web typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/web package.json pnpm-lock.yaml
git commit -m "实现 VOC Hub 基础证据视图"
```

## Task 12: End-to-End Smoke and Documentation

**Files:**
- Create: `tests/fixtures/amazon-review-page.html`
- Create: `tests/fixtures/reddit-thread.json`
- Modify: `README.md`
- Modify: `docs/product/product-prd-voc-browser-plugin-mvp-review.md`

- [ ] **Step 1: Add smoke fixtures**

Create `tests/fixtures/amazon-review-page.html`:

```html
<div data-hook="review" id="R123">
  <i data-hook="review-star-rating"><span>2.0 out of 5 stars</span></i>
  <a data-hook="review-title"><span>Breaks fast</span></a>
  <span data-hook="review-body"><span>The switch broke after two weeks.</span></span>
  <span data-hook="avp-badge">Verified Purchase</span>
</div>
```

Create `tests/fixtures/reddit-thread.json`:

```json
[
  {
    "kind": "Listing",
    "data": {
      "children": [
        {
          "kind": "t3",
          "data": {
            "name": "t3_thread123",
            "id": "thread123",
            "title": "Quiet grinder?",
            "selftext": "Need a quiet grinder.",
            "subreddit": "Coffee",
            "created_utc": 1780602718
          }
        }
      ]
    }
  },
  {
    "kind": "Listing",
    "data": {
      "children": [
        {
          "kind": "t1",
          "data": {
            "name": "t1_comment456",
            "id": "comment456",
            "body": "Noise is the real issue.",
            "parent_id": "t3_thread123",
            "link_id": "t3_thread123",
            "depth": 0,
            "replies": ""
          }
        }
      ]
    }
  }
]
```

- [ ] **Step 2: Add README local run commands**

Append to `README.md`:

````md
## Local Development

Run backend:

```bash
cd apps/api
uv run uvicorn plugin_hub_api.main:app --reload --port 8000
```

Run VOC Hub:

```bash
pnpm --filter @plugin-hub/web dev
```

Run extension tests:

```bash
pnpm --filter @plugin-hub/extension test
```

Run backend tests:

```bash
cd apps/api
uv run pytest
```
````

- [ ] **Step 3: Run full verification**

Run:

```bash
cd apps/api && uv run pytest
cd ../..
pnpm test
pnpm typecheck
```

Expected: backend tests pass; extension/web Vitest suites pass; TypeScript strict checks pass.

- [ ] **Step 4: Update PRD status note**

Append to `docs/product/product-prd-voc-browser-plugin-mvp-review.md`:

```md
## 18. Implementation Plan Link

The reviewed implementation plan is stored at:

- `docs/workflows/workflow-implementation-plan-voc-browser-plugin-mvp-review.md`
```

- [ ] **Step 5: Commit**

```bash
git add README.md tests/fixtures docs/product/product-prd-voc-browser-plugin-mvp-review.md
git commit -m "补充 MVP 验收样本与运行说明"
```

## Plan Self-Review

Spec coverage:

- Product positioning and P0 scope are covered by Tasks 1, 11, and 12.
- Amazon collection and pagination context are covered by Tasks 3 and 8.
- Reddit `.json`, comment tree, and `more` node handling are covered by Tasks 4 and 9.
- `Collection Method Audit` is represented through coverage fields, stop reasons, quality flags, fixtures, and smoke verification in Tasks 2, 3, 4, 8, 9, and 12.
- Schema fusion model A is covered by Tasks 2, 3, 4, 5, and 6.
- Private server ingest is covered by Task 5.
- VOC Hub is covered by Task 11.
- Traceable strategy output is covered by Task 6.

Placeholder scan:

- No placeholder markers from the writing-plans red-flag list remain.
- Each implementation task has exact files, commands, expected results, and commit commands.

Type consistency:

- Backend contract names are consistent: `RawSourceItem`, `CanonicalVocUnit`, `CollectionRunCreate`, `Platform`, `SourceKind`.
- Extension contract names mirror backend payload names: `CollectionRunPayload`, `RawSourceItem`.
- API route paths are consistent: `/api/collection-runs` and `/api/voc-units`.

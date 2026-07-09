---
title: Plugin Hub Release Version Alignment Runbook
doc_type: runbook
module: product_engineering
topic: plugin-hub-release-version-alignment
status: draft
created: 2026-07-01
updated: 2026-07-01
owner: self
source: codex
---

# Plugin Hub Release Version Alignment Runbook

## 1. Purpose

Loop 5 resolves the gap between locally verified Loop 2/3 capabilities and production read-only observations.

This runbook does not authorize deployment. It defines the release candidate boundary, verification gates, and post-release read-only checks needed before saying the local Loop 2/3 capabilities are observable in production.

## 2. Evidence Inventory

| Evidence | Path / Command | Grade | Result |
| --- | --- | --- | --- |
| Production read-only smoke | `output/production-readonly/20260701T024920Z/summary.tsv` | L3-production-read-only | Production public GET checks recorded current route behavior. |
| Local contract probe | `output/release-alignment/20260701T031215Z/local_contract_probe.json` | L1-local-runtime | Local TestClient observed `voc-signals` route and capability evidence-label fields. |
| Invalid local probe marker | `output/release-alignment/20260701T031155Z/INVALID_RUN.txt` | invalid | Earlier relative-path attempt produced no valid evidence artifact. |
| API scoped lint | `uv --directory apps/api run ruff check ...` | L1-local-runtime | Passed. |
| API scoped tests | `uv --directory apps/api run pytest tests/test_insights.py tests/test_capture_capabilities_api.py tests/test_capture_authorizations_api.py tests/test_contracts.py` | L1-local-runtime | 41 passed, 1 existing Starlette/httpx deprecation warning. |
| API typecheck | `uv --directory apps/api run mypy` | L1-local-runtime | Passed. |
| Web API tests | `node_modules/.bin/vitest run tests/api.test.ts` from `apps/web` | L1-local-runtime | 27 passed. |
| Web typecheck | `node_modules/.bin/tsc --noEmit` from `apps/web` | L1-local-runtime | Passed. |

## 3. Local vs Production Alignment Matrix

| Capability | Local Evidence | Production Observation | Alignment Decision |
| --- | --- | --- | --- |
| `GET /api/insights/voc-signals?platform=amazon` | Local probe returned 200 with `enriched_voc_signals` and `relation_edges`; scoped tests cover signal generation. | Production returned 404. | Requires API release before this can be called a production-observed capability. |
| `GET /api/capture-capabilities` evidence labels | Local probe returned 4 items and all carried `evidence_grade`, `next_required_action`, and `side_effect_boundary`. | Production returned 200 but lacked those fields. | Requires API release; if Web parser requiring these fields is released, API must be aligned at the same time or first. |
| `GET /api/insights/strategy-notes?platform=amazon` | Local tests cover signal-backed strategy notes. | Production returned 200 with 4 strategy-note groups. | Keep as a regression guard in post-release smoke. |
| DB schema | Loop 2/3 local changes are response/derived-asset changes; no persistent relation/signal tables were added. | Production DB remains SQLite through `/data/plugin_hub.db`. | No schema migration is required for this release candidate; DB mutation remains separately gated. |
| Instagram Graph live-read | Local capability/preflight labels are contract-verified. | Production Graph path remains credential-gated in public capability observation. | Keep live-read blocked until platform rights, backend-only credential setup, task approval, and explicit live-read authorization exist. |

## 4. Release Candidate Boundary

Current worktree is a mixed dirty tree across API, Web, Extension, deploy, scripts, docs, and output artifacts. Do not release the entire worktree as a Loop 2/3-only change without a separate file inventory.

Minimum release candidate set to review:

| Area | Files |
| --- | --- |
| API signal endpoint | `apps/api/src/plugin_hub_api/routes/insights.py`, `apps/api/src/plugin_hub_api/services/insights.py`, `apps/api/src/plugin_hub_api/schemas.py` |
| API capability labels | `apps/api/src/plugin_hub_api/routes/capture_capabilities.py`, `apps/api/src/plugin_hub_api/routes/capture_authorizations.py` |
| API tests | `apps/api/tests/test_insights.py`, `apps/api/tests/test_contracts.py`, `apps/api/tests/test_capture_capabilities_api.py`, `apps/api/tests/test_capture_authorizations_api.py` |
| Web contract parser | `apps/web/src/lib/api.ts`, `apps/web/tests/api.test.ts` |
| Docs/runbooks | `docs/workflows/plugin-hub-production-evidence-governance-runbook-draft-20260701.md`, this runbook |

If unrelated changed files are included in a release branch, they need their own test and evidence claims.

## 5. Pre-Release Gate

The release can move to a deploy proposal only after all of the following are true:

1. Release branch or staging set contains a reviewed file inventory.
2. API scoped lint, API scoped tests, API typecheck, Web API tests, and Web typecheck pass from a clean command transcript.
3. Full API/Web/Extension package tests are either run or explicitly deferred with a documented reason.
4. Docker image build or deployment package build is run in the same release context.
5. Production database backup plan is recorded, even when no schema migration is expected.
6. Post-release read-only smoke command is prepared with quoted URLs and absolute tool paths.
7. Human approval exists for the deploy window.

## 6. Post-Release Read-Only Smoke

After an approved release, create a fresh directory under:

```text
output/production-readonly/<UTC>/
```

Minimum expected observations:

| Route | Expected Status | Expected Shape |
| --- | --- | --- |
| `/api/insights/voc-signals?platform=amazon` | 200 | `enriched_voc_signals`, `relation_edges` |
| `/api/capture-capabilities` | 200 | every item includes `evidence_grade`, `next_required_action`, `side_effect_boundary` |
| `/api/insights/strategy-notes?platform=amazon` | 200 | `items` |
| `/api/voc-units?platform=amazon` | 200 | `items` |
| `/api/voc-units?platform=reddit` | 200 | `items` |

Only after this post-release read-only smoke passes can the Loop 2/3 capabilities be described as production-observed.

## 7. Rollback Boundary

Rollback must be versioned and evidence-backed:

1. Record previous image or release reference before deployment.
2. Keep the production database backup plan separate from app rollback.
3. If post-release smoke shows route or parser drift, roll back app images first and re-run the read-only smoke.
4. Do not use rollback as a reason to run live platform capture or database mutation.

## 8. Next Loop Recommendation

Loop 6 should be one of two paths:

| Path | When To Choose | Output |
| --- | --- | --- |
| Release packaging | User approves preparing a release candidate branch or deploy package. | File inventory, full test/build transcript, deploy proposal. |
| Evidence model persistence | Leadership requires audit/history for `relation_edges` and `enriched_voc_signal`. | DB migration proposal, backfill dry-run plan, rollback plan. |

## 9. Loop 6 Decision

Loop 6 selected release packaging preparation without production deployment.

Decision record:

```text
docs/workflows/plugin-hub-loop6-path-selection-decision-draft-20260701.md
```

Evidence-model persistence remains deferred until leadership requires persistent audit/history or a database migration window is explicitly approved.

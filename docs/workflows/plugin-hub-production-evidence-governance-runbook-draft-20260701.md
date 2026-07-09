---
title: Plugin Hub Production Evidence Governance Runbook
doc_type: runbook
module: product_engineering
topic: plugin-hub-production-evidence-governance
status: draft
created: 2026-07-01
updated: 2026-07-01
owner: self
source: codex
---

# Plugin Hub Production Evidence Governance Runbook

## 1. Purpose

This runbook defines how Plugin Hub production evidence is collected, labeled, stored, and promoted.

The operating rule is:

```text
local / fixture / dry-run / production read-only / authorized live side effect are separate evidence layers.
```

Loop 4 closes only the production read-only governance layer. It does not approve platform live capture, provider calls, production database mutation, or production VOC writes.

## 2. Evidence Grade Contract

| Grade | Meaning | Allowed Claim | Forbidden Claim |
| --- | --- | --- | --- |
| L0-unverified | Assertion without fresh reproducible evidence | "needs verification" | "works" |
| L1-public-or-runtime | Local runtime, static check, or public runtime reachability | "runtime reachable" | "production data path is complete" |
| L2-fixture-or-dry-run | Controlled fixture or dry-run without external side effect | "contract/preflight passed" | "live platform capture completed" |
| L3-production-read-only | Production observation through read-only GET/browser checks | "production currently exposes this read-only behavior" | "deployment includes unobserved local changes" |
| L4-authorized-live | Explicit approval plus logged live side effect | "approved live action completed" | any broader action than the approved scope |

## 3. 2026-07-01 Production Read-Only Smoke

Evidence directory:

```text
output/production-readonly/20260701T024920Z/
```

| Check | URL | Status | Evidence | Interpretation |
| --- | --- | --- | --- | --- |
| Web shell | `https://plugin.lute-tlz-dddd.top/` | 200 | `root.body`, `root.headers` | Production web entry is reachable. |
| Capture capability | `/api/capture-capabilities` | 200 | `capture-capabilities.body` | Production exposes capability inventory, but current production response does not include Loop 3 evidence-label fields. |
| Amazon VOC units | `/api/voc-units?platform=amazon` | 200 | `voc-units-amazon.body` | Production read-only Amazon VOC data is observable; 10 returned items in this sampled response. |
| Reddit VOC units | `/api/voc-units?platform=reddit` | 200 | `voc-units-reddit.body` | Production read-only Reddit VOC data is observable; 340 returned items in this sampled response. |
| Amazon strategy notes | `/api/insights/strategy-notes?platform=amazon` | 200 | `strategy-notes-amazon.body` | Production returns 4 deterministic strategy-note groups. |
| Amazon VOC signals | `/api/insights/voc-signals?platform=amazon` | 404 | `voc-signals-amazon.body` | Local Loop 2 signal endpoint is not proven deployed in production. Treat this as deployment/version drift, not as production-ready evidence. |

Additional observation:

- The smoke summary recorded `contains_sensitive_marker=false` for all captured response/header files.
- The smoke used public GET requests only.
- No authorization preflight POST, worker start, provider call, live platform capture, production write, or database mutation was performed.

## 4. Supported And Blocked Statements

Supported after this smoke:

- The public HTTPS route for Plugin Hub is reachable.
- Public read-only API routes for capture capabilities, Amazon VOC units, Reddit VOC units, and Amazon strategy notes respond successfully.
- Production has observable VOC data for Amazon and Reddit in the sampled read-only responses.

Blocked after this smoke:

- Do not claim the local Loop 2 `voc-signals` endpoint is deployed to production; the public route returned 404.
- Do not claim production capability responses already carry Loop 3 `evidence_grade`, `next_required_action`, or `side_effect_boundary`; the public response lacked these fields.
- Do not claim authorized Instagram Graph live-read readiness; production still reports the Graph path as credential-gated.
- Do not claim production database migration, schema upgrade, or backfill was executed.

## 5. Repeatable Read-Only Smoke Checklist

Before a release or leadership readout:

1. Create a timestamped directory under `output/production-readonly/<UTC>/`.
2. Run only public GET/browser checks unless a separate approval exists.
3. Capture response body, response headers, status code, content type, body size, and credential-marker scan result.
4. Summarize counts without copying raw user-generated content into reports.
5. Label the evidence as `L3-production-read-only` only for the exact production behavior observed.
6. Record route drift explicitly when production differs from local implementation.

Minimum routes:

| Route | Purpose |
| --- | --- |
| `/` | Web shell reachability |
| `/api/capture-capabilities` | Platform capability inventory |
| `/api/voc-units?platform=amazon` | Amazon read-only VOC visibility |
| `/api/voc-units?platform=reddit` | Reddit read-only VOC visibility |
| `/api/insights/strategy-notes?platform=amazon` | Strategy-note visibility |
| `/api/insights/voc-signals?platform=amazon` | Deployment drift check for Loop 2 signal endpoint |

## 6. Evidence Index

| Evidence Class | Current Path | Retention Rule |
| --- | --- | --- |
| Loop 1 local screenshots | `output/playwright/loop1-visual/` | Keep while the Loop 1 UX claim is active. |
| Loop 4 production smoke | `output/production-readonly/20260701T024920Z/` | Keep until replaced by a newer production smoke for the same release. |
| Persistent plan state | `.kiro/plan/task_plan.md`, `.kiro/plan/progress.md`, `.kiro/plan/findings.md` | Update after every loop. |
| Reusable governance docs | `docs/workflows/` | Keep with frontmatter and evidence-grade labels. |

Do not treat untracked output artifacts as release state by themselves. A release or deployment claim still needs a deploy record, version reference, and fresh production read-only evidence.

## 7. Database Upgrade Boundary

Current facts:

- Local API defaults to `sqlite+pysqlite:///./plugin_hub.db`.
- Production compose sets the API and worker database URL to `sqlite+pysqlite:////data/plugin_hub.db`.
- Production compose mounts `/opt/plugin-hub/data` into `/data`.
- API startup calls SQLAlchemy `Base.metadata.create_all(bind=engine)`.
- No Alembic or equivalent migration framework is currently configured.

Implications:

- `create_all` can create missing tables, but it is not a complete schema migration system.
- Any future persistent `relation_edges` or `enriched_voc_signal` table needs an explicit migration and backfill plan.
- Production database change evidence must not be inferred from local tests, route availability, or Docker health checks.

Required gates before a production database change:

1. Schema diff reviewed in code.
2. Production database backup or volume snapshot plan reviewed.
3. Migration dry-run executed against a copied database, not the live production file.
4. Read-only row counts and route smoke recorded before the change.
5. Explicit approval for the exact production mutation window.
6. Post-change read-only verification recorded in a new evidence directory.
7. Rollback path recorded with the same approval boundary.

## 8. Next Value Step

To raise the evidence grade for Loop 2 and Loop 3 work:

1. Deploy the local API/Web changes through the approved release path.
2. Re-run this production read-only smoke.
3. Confirm `/api/insights/voc-signals` returns 200 in production.
4. Confirm `/api/capture-capabilities` includes evidence-label fields in production.
5. Keep Instagram Graph live-read blocked until platform rights, backend-only credential configuration, and explicit live-read approval are present.

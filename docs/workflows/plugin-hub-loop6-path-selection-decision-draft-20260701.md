---
title: Plugin Hub Loop 6 Path Selection Decision
doc_type: decision_record
module: product_engineering
topic: plugin-hub-loop6-path-selection
status: draft
created: 2026-07-01
updated: 2026-07-01
owner: self
source: codex
---

# Plugin Hub Loop 6 Path Selection Decision

## 1. Decision

Choose **release packaging preparation without production deployment** as the next loop.

Evidence-model persistence is deferred until one of these conditions is true:

- leadership explicitly requires persisted audit/history for `relation_edges` and `enriched_voc_signal`;
- the local Loop 2/3 API capability is already production-observed and the next value gap becomes history/backfill;
- a database migration window is explicitly approved.

This decision does not authorize production deployment, production database mutation, provider calls, platform live capture, or Chrome Web Store release.

## 2. Why This Path

Current highest-value gap:

```text
local Loop 2/3 capability exists -> production public route does not yet expose it
```

Loop 5 showed:

- local `/api/insights/voc-signals?platform=amazon` returns 200 with `enriched_voc_signals` and `relation_edges`;
- production `/api/insights/voc-signals?platform=amazon` returns 404;
- local `/api/capture-capabilities` includes evidence-label fields;
- production `/api/capture-capabilities` does not expose those fields;
- current implementation does not require new DB tables for Loop 2/3.

Therefore, the next highest-value action is to make the release candidate reviewable and packageable. Adding persistence first would introduce migration/backfill risk before the product value is visible in production.

## 3. Option Matrix

| Option | Value Unlocked | Main Risk | Evidence Needed | Decision |
| --- | --- | --- | --- | --- |
| Release packaging preparation | Turns local signal/capability work into a deployable candidate and clears production route drift. | Mixed dirty tree may ship unrelated changes if inventory is weak. | File inventory, full local gates, build/package proof, DB backup plan, post-release smoke plan. | Choose. |
| Evidence-model persistence proposal | Enables audit/history for derived signal assets. | Requires schema design, migration, backfill, rollback, and production data handling. | Schema proposal, migration dry-run plan, copied-DB backfill proof. | Defer. |

## 4. Loop Engineering Components

### Goal

Prepare a release candidate package for Loop 2/3 without performing production side effects.

Completion means:

- release candidate file inventory is explicit;
- included and excluded dirty-tree files are separated;
- full test/build gate is defined and, if run, recorded;
- production DB backup plan is documented;
- post-release read-only smoke is ready;
- deploy approval remains a separate gate.

### State

| State Item | Current Fact | Evidence Grade |
| --- | --- | --- |
| Local signal route | `GET /api/insights/voc-signals?platform=amazon` returns 200 in TestClient. | L1-local-runtime |
| Local capability labels | all 4 local capability items include evidence labels. | L1-local-runtime |
| Production signal route | production returns 404 for `voc-signals`. | L3-production-read-only |
| Production capability labels | production capability response lacks local evidence-label fields. | L3-production-read-only |
| DB schema | no persistent signal/relation tables in current implementation. | repo inspection |
| Worktree | broad tracked/untracked changes across API, Web, Extension, deploy, docs, output. | git status |
| Authorization | no explicit production deploy approval in this loop. | conversation state |

### Action

Loop 7 should prepare a release package, not deploy it:

1. Build a release file inventory from `git status`.
2. Classify files as `include`, `exclude`, or `needs-review`.
3. Run full local gates or document any deferred gate:
   - `uv --directory apps/api run pytest`
   - `uv --directory apps/api run ruff check .`
   - `uv --directory apps/api run mypy`
   - package-level Web tests, lint, typecheck, build
   - package-level Extension tests, lint, typecheck, build
   - `git diff --check`
4. Run Docker/package build proof if release packaging remains the chosen path.
5. Prepare DB backup and rollback plan without touching production.
6. Prepare post-release read-only smoke commands with quoted URLs and absolute tool paths.

### Evaluation

| Gate | Pass Condition | If It Does Not Pass |
| --- | --- | --- |
| File inventory | every dirty file is classified. | split the release or stop for user review. |
| Local gates | API/Web/Extension gates pass in package context. | keep release at local-fix stage. |
| Build/package | API/Web images or deploy package build succeeds. | do not request deploy approval. |
| DB backup plan | backup/rollback path is documented. | do not request deploy approval. |
| Post-release smoke plan | exact GET checks and expected shapes are documented. | do not request deploy approval. |
| Approval | user explicitly approves deploy window and scope. | keep package as review-ready only. |

### Memory / Feedback

Update:

- `.kiro/plan/task_plan.md`
- `.kiro/plan/progress.md`
- `.kiro/plan/findings.md`
- `docs/workflows/plugin-hub-release-version-alignment-runbook-draft-20260701.md`

Only write self-evolution candidates for concrete failure, user correction, or failed verification, and avoid duplicating existing `uv --directory` / evidence-grade lessons.

## 5. Next Loop Contract

Loop 7 title:

```text
release packaging preparation, no production deploy
```

Allowed:

- read repo state;
- create file inventory;
- run local tests/lint/typecheck/build;
- generate local release-readiness artifacts;
- update docs and `.kiro/plan`.

Blocked until explicit approval:

- production deploy;
- remote server mutation;
- production DB backup execution;
- production DB migration;
- provider call;
- platform live capture;
- Chrome Web Store submission.

## 6. Leadership Framing

This path is the fastest way to turn the project from "local capability exists" into "production-observed capability can be proven after release".

For cross-border ecommerce use cases, the business value is direct:

- VOC signal endpoint unlocks traceable product/review signals for listing, ad ROI, and localization decisions.
- capability evidence labels keep platform expansion compliant and auditable.
- release packaging discipline prevents unrelated dirty-tree changes from entering a production candidate.

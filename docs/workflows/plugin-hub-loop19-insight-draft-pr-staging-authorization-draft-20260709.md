---
title: Plugin Hub Loop 19 Insight Draft PR Staging Authorization
doc_type: workflow_draft
module: release_governance
topic: insight-brief-draft-pr-staging
status: draft
created: 2026-07-09
updated: 2026-07-09
owner: self
source: human+ai
---

# Plugin Hub Loop 19 Insight Draft PR Staging Authorization

## Purpose

Prepare an explicit file-list authorization packet for the Loop 15-18 insight release candidate.

This packet is limited to review and authorization preparation. It does not execute `git add`, commit, push, Draft PR creation, merge, production deployment, remote mutation, production database operation, provider call, live platform capture, manual Chrome acceptance, or Chrome Web Store submission.

## Current Facts

- Workspace: `/Users/pray/project/plugin_hub`.
- Branch: `implementation/voc-browser-plugin-mvp...origin/main [ahead 8]`.
- HEAD: `6361607bf8ad` (`Fix Reddit DOM fallback and upload diagnostics`).
- Loop 18 current packet: `docs/workflows/plugin-hub-loop18-insight-release-approval-refresh-draft-20260709.md`.
- Loop 18 local gates passed across API, Web, Extension, package generation, package verification, and Docker Compose config preflight.
- Current release candidate remains unstaged.

## Required Runtime Source And Tests

The following files form the required Draft PR runtime source/test set for the professional insight candidate.

### Backend InsightBrief

```text
apps/api/src/plugin_hub_api/routes/insights.py
apps/api/src/plugin_hub_api/schemas.py
apps/api/src/plugin_hub_api/services/insights.py
apps/api/tests/test_contracts.py
apps/api/tests/test_insights.py
```

Reason: these files add and verify the backend `InsightBrief` contract, deterministic Reddit/Amazon templates, and `/api/insights/briefs`.

### Web VOC Diagnosis

```text
apps/web/src/lib/api.ts
apps/web/src/components/InsightBriefPanel.tsx
apps/web/app/page.tsx
apps/web/app/globals.css
apps/web/tests/api.test.ts
apps/web/tests/insight-brief-panel.test.tsx
```

Reason: these files add and verify the VOC Hub `VOC 经营诊断` Web surface, typed API parsing, component rendering, dashboard integration, and responsive styling.

### Extension Short Diagnosis

```text
apps/extension/src/types/contracts.ts
apps/extension/src/types/messages.ts
apps/extension/src/lib/upload-client.ts
apps/extension/src/background/service-worker.ts
apps/extension/src/content/ui/ContentCommandBar.tsx
apps/extension/src/content/ui/content-command-bar.css.ts
apps/extension/tests/upload-client.test.ts
apps/extension/tests/content-command-bar-render.test.tsx
```

Reason: these files add and verify the Extension short `经营诊断` contract, parser, runtime message, service-worker path, drawer rendering, and compact styles.

## Recommended Review Documents

These files are recommended for the Draft PR if the reviewer wants the product rationale and local evidence in the same review unit.

```text
docs/product/plugin-hub-insight-redesign-prd-draft-20260708.md
docs/workflows/plugin-hub-loop18-insight-release-approval-refresh-draft-20260709.md
docs/workflows/plugin-hub-loop19-insight-draft-pr-staging-authorization-draft-20260709.md
```

Reason: they preserve the product direction, evidence record, and exact staging boundary for reviewer context.

## Hold Out Of Staging By Default

These paths should stay out of Draft PR staging unless the owner explicitly promotes them.

```text
.kiro/plan/
output/
tmp/outputs/
drafts/analysis/
scripts/browser-harness/
docs/workflows/plugin-hub-loop9-release-approval-packet-draft-20260706.md
docs/workflows/plugin-hub-loop13-release-approval-refresh-draft-20260708.md
```

Reason:

- `.kiro/plan/` is local working-plan state.
- `output/` and `tmp/outputs/` are local evidence/package artifacts.
- `drafts/analysis/` is business-analysis background material, not runtime source.
- `scripts/browser-harness/` is diagnostic tooling from the local acceptance lane.
- Loop 9 and Loop 13 packets are older review packets superseded for the current insight candidate by Loop 18 and this Loop 19 packet.

## Proposed Command Set

The following commands are proposals only. They were not executed in Loop 19.

Required runtime source/test set:

```bash
git add -- \
  apps/api/src/plugin_hub_api/routes/insights.py \
  apps/api/src/plugin_hub_api/schemas.py \
  apps/api/src/plugin_hub_api/services/insights.py \
  apps/api/tests/test_contracts.py \
  apps/api/tests/test_insights.py \
  apps/web/src/lib/api.ts \
  apps/web/src/components/InsightBriefPanel.tsx \
  apps/web/app/page.tsx \
  apps/web/app/globals.css \
  apps/web/tests/api.test.ts \
  apps/web/tests/insight-brief-panel.test.tsx \
  apps/extension/src/types/contracts.ts \
  apps/extension/src/types/messages.ts \
  apps/extension/src/lib/upload-client.ts \
  apps/extension/src/background/service-worker.ts \
  apps/extension/src/content/ui/ContentCommandBar.tsx \
  apps/extension/src/content/ui/content-command-bar.css.ts \
  apps/extension/tests/upload-client.test.ts \
  apps/extension/tests/content-command-bar-render.test.tsx
```

Recommended review documents:

```bash
git add -- \
  docs/product/plugin-hub-insight-redesign-prd-draft-20260708.md \
  docs/workflows/plugin-hub-loop18-insight-release-approval-refresh-draft-20260709.md \
  docs/workflows/plugin-hub-loop19-insight-draft-pr-staging-authorization-draft-20260709.md
```

Local planning state, local evidence artifacts, older packets, analysis drafts, and diagnostic tooling should remain unstaged by default.

## Verification Plan

Before executing any authorized staging command, rerun:

```bash
git status --short --branch
git diff --check -- \
  apps/api/src/plugin_hub_api/routes/insights.py \
  apps/api/src/plugin_hub_api/schemas.py \
  apps/api/src/plugin_hub_api/services/insights.py \
  apps/api/tests/test_contracts.py \
  apps/api/tests/test_insights.py \
  apps/web/src/lib/api.ts \
  apps/web/src/components/InsightBriefPanel.tsx \
  apps/web/app/page.tsx \
  apps/web/app/globals.css \
  apps/web/tests/api.test.ts \
  apps/web/tests/insight-brief-panel.test.tsx \
  apps/extension/src/types/contracts.ts \
  apps/extension/src/types/messages.ts \
  apps/extension/src/lib/upload-client.ts \
  apps/extension/src/background/service-worker.ts \
  apps/extension/src/content/ui/ContentCommandBar.tsx \
  apps/extension/src/content/ui/content-command-bar.css.ts \
  apps/extension/tests/upload-client.test.ts \
  apps/extension/tests/content-command-bar-render.test.tsx \
  docs/product/plugin-hub-insight-redesign-prd-draft-20260708.md \
  docs/workflows/plugin-hub-loop18-insight-release-approval-refresh-draft-20260709.md \
  docs/workflows/plugin-hub-loop19-insight-draft-pr-staging-authorization-draft-20260709.md
git diff --cached --check
git diff --cached --name-status
```

If staging is authorized, run `git diff --cached --name-status` immediately after staging and compare it with this packet before committing or opening a Draft PR.

## Authorization Boundary

Owner approval must be explicit before each next side-effect layer:

- Stage the exact source/test list.
- Stage the recommended review docs.
- Create a commit.
- Push the branch.
- Open a Draft PR.
- Mark a PR ready for review.
- Merge.
- Deploy.
- Run production checks beyond read-only probes.
- Perform live platform capture or provider calls.
- Submit any Chrome Web Store package.

## Loop 19 Local Acceptance Record

Local document hygiene checks completed in this loop:

- Passed: all proposed required source/test files, recommended review docs, and planning files exist (`all_exist:25`).
- Passed: `git diff --check` for the required source/test files, recommended review docs, this packet, and `.kiro/plan` updates.
- Passed: `git diff --cached --name-status` produced no staged entries.
- Passed: `git diff --cached --check` produced no output.
- Observed: final branch remained `implementation/voc-browser-plugin-mvp...origin/main [ahead 8]`.
- Observed: release candidate files remained unstaged; no `git add`, commit, push, Draft PR creation, merge, deploy, provider call, live capture, manual Chrome acceptance, or Web Store submission was performed.

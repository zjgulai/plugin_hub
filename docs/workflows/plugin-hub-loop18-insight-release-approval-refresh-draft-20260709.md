---
title: Plugin Hub Loop 18 Insight Release Approval Refresh
doc_type: approval_packet
module: product_engineering
topic: plugin-hub-loop18-insight-release-approval-refresh
status: draft
created: 2026-07-09
updated: 2026-07-09
owner: self
source: codex
---

# Plugin Hub Loop 18 Insight Release Approval Refresh

## 1. Objective

Create a fresh review packet for the Loop 15-17 insight work before any git staging, PR, merge, or deployment decision.

This packet covers:

- Loop 15 backend `InsightBrief` contract and deterministic Reddit/Amazon templates.
- Loop 16 Web `VOC 经营诊断` workbench.
- Loop 17 Extension short `经营诊断` card.

Boundary:

```text
production unchanged / no git stage / no commit / no push / no PR / no merge / no production deploy / no provider call
```

## 2. Current Branch Facts

| Item | Value |
| --- | --- |
| Current branch | `implementation/voc-browser-plugin-mvp` |
| Release base | `origin/main` |
| Current HEAD | `6361607bf8adb42c4848b10b32851cb4a1c53561` |
| Current HEAD subject | `Fix Reddit DOM fallback and upload diagnostics` |
| Ahead of `origin/main` | 8 commits |
| `origin/main` ancestry | `origin/main` is an ancestor of HEAD |
| Committed file scope | 123 files changed against `origin/main` |

Interpretation:

- The committed branch still represents the earlier broad VOC browser-plugin release stack through Loop 12.
- Loop 15-17 insight work is currently unstaged local source/test/doc state.
- A later staging or PR step must explicitly choose whether to include these insight files in the release candidate.

## 3. Insight Candidate File Scope

### Backend Insight Contract

| Path | Purpose |
| --- | --- |
| `apps/api/src/plugin_hub_api/schemas.py` | Backend `InsightBrief` and nested schema contract. |
| `apps/api/src/plugin_hub_api/services/insights.py` | Deterministic Reddit/Amazon insight brief generation. |
| `apps/api/src/plugin_hub_api/routes/insights.py` | `GET /api/insights/briefs` route. |
| `apps/api/tests/test_contracts.py` | Contract coverage for advisor evidence and confidence. |
| `apps/api/tests/test_insights.py` | Route/service coverage for Reddit/Amazon briefs. |

### Web VOC Hub Diagnosis

| Path | Purpose |
| --- | --- |
| `apps/web/src/lib/api.ts` | Web `InsightBrief` parser and `fetchInsightBriefs`. |
| `apps/web/src/components/InsightBriefPanel.tsx` | Full VOC Hub diagnosis panel. |
| `apps/web/app/page.tsx` | Dashboard data load and panel placement. |
| `apps/web/app/globals.css` | Web diagnosis panel layout and responsive CSS. |
| `apps/web/tests/api.test.ts` | Web API parser coverage. |
| `apps/web/tests/insight-brief-panel.test.tsx` | Web panel render coverage. |

### Extension Short Diagnosis

| Path | Purpose |
| --- | --- |
| `apps/extension/src/types/contracts.ts` | Extension `InsightBrief` contract. |
| `apps/extension/src/types/messages.ts` | `PLUGIN_HUB_GET_INSIGHT_BRIEFS` runtime message. |
| `apps/extension/src/lib/upload-client.ts` | Extension `getInsightBriefs` parser/fetcher. |
| `apps/extension/src/background/service-worker.ts` | Background message handling for insight brief reads. |
| `apps/extension/src/content/ui/ContentCommandBar.tsx` | Compact `经营诊断` rendering in the drawer. |
| `apps/extension/src/content/ui/content-command-bar.css.ts` | Compact diagnosis card styling. |
| `apps/extension/tests/upload-client.test.ts` | Extension client parser coverage. |
| `apps/extension/tests/content-command-bar-render.test.tsx` | Drawer behavior coverage. |

### Product / Planning / Evidence Lanes

| Lane | Paths | Release treatment |
| --- | --- | --- |
| Product design draft | `docs/product/plugin-hub-insight-redesign-prd-draft-20260708.md` | Include only if review wants product rationale alongside source. |
| Approval packet docs | `docs/workflows/plugin-hub-loop18-insight-release-approval-refresh-draft-20260709.md` | Review artifact, not app runtime code. |
| Local planning state | `.kiro/plan/*` | Keep local unless explicitly promoted. |
| Local evidence | `output/`, `tmp/outputs/` | Evidence only; do not stage as source. |
| Split analysis drafts | `drafts/analysis/*` | Keep out of app release. |
| Diagnostic tooling | `scripts/browser-harness/` | Keep separate from this insight release packet. |

## 4. Development / Test / Acceptance Plan

### Development

- Do not modify business source in Loop 18 unless a local gate isolates a bounded blocker.
- Keep Loop 18 as a review-packet and local-gate refresh.
- Keep Web, Extension, and backend insight layers together in review because the same `InsightBrief` contract binds them.

### Testing

Run fresh local gates:

1. API: ruff, mypy, scoped insight tests, full pytest.
2. Web: Vitest, ESLint, `next typegen && tsc --noEmit`, `next build`.
3. Extension: Vitest, ESLint, TypeScript, Amazon/Reddit/Instagram builds, package, verifier.
4. Diff hygiene: `git diff --check` for touched source/test/docs/planning files.

### Deployment

Loop 18 deployment is local artifact refresh only:

- Web production build can complete locally.
- Extension zip/unpacked package can be refreshed under `tmp/outputs/`.
- No production host is contacted.
- No production container is restarted.
- No production database operation is executed.

### Acceptance

Loop 18 can close only if:

- this packet exists with frontmatter;
- local gates pass or blockers are isolated;
- final side-effect boundary is recorded;
- no git staging, commit, push, PR, merge, production deployment, provider call, live platform capture, or Chrome Web Store submission is performed.

## 5. Verification Results

Loop 18 local gates passed:

| Gate | Result |
| --- | --- |
| API scoped ruff | passed |
| API mypy | passed: no issues in 26 source files |
| API scoped insight tests | passed: 35 tests, 1 existing Starlette/httpx warning |
| API full pytest | passed: 140 tests, 1 existing Starlette/httpx warning |
| Web Vitest | passed: 32 tests |
| Web ESLint | passed |
| Web `next typegen && tsc --noEmit` | passed; Next emitted the existing multiple-lockfile workspace-root warning |
| Web `next build` | passed; Next emitted the same multiple-lockfile workspace-root warning |
| Extension Vitest | passed: 97 tests |
| Extension ESLint | passed |
| Extension TypeScript | passed with bundled Node and TypeScript CLI |
| Extension Amazon build | passed |
| Extension Reddit build | passed |
| Extension Instagram build | passed |
| Tencent Lighthouse Docker Compose config | passed |
| Extension package generation | passed: three zip/unpacked outputs generated under `tmp/outputs/` |
| Extension package verifier | passed: `ok=true`, 15 zip entries per target |

Package verifier details:

| Target | Manifest | Version | Content script size | Zip entries |
| --- | ---: | --- | ---: | ---: |
| Amazon | 3 | `0.1.0` | 253695 | 15 |
| Reddit | 3 | `0.1.0` | 256368 | 15 |
| Instagram | 3 | `0.1.0` | 244445 | 15 |

Local artifact result:

- Amazon zip: `tmp/outputs/plugin-hub-amazon-voc-0.1.0.zip`
- Reddit zip: `tmp/outputs/plugin-hub-reddit-voc-0.1.0.zip`
- Instagram zip: `tmp/outputs/plugin-hub-instagram-voc-0.1.0.zip`
- Corresponding unpacked directories were refreshed under `tmp/outputs/`.

No production host was contacted, no production container was restarted, no production database operation was executed, and no provider API was called.

## 6. Next Authorization Boundary

After this packet is reviewed, choose exactly one next gate:

| Option | Meaning |
| --- | --- |
| Draft PR authorization | Stage and push an approved file list, then create a Draft PR. This is not production deploy approval. |
| Manual Chrome acceptance | Reload the unpacked extension in the user's Chrome and collect real browser evidence. This is not PR or deploy approval. |
| Production deploy packet | Create a separate deploy packet with backup, rollback, remote commands, and post-release public read-only smoke. |

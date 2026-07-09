---
title: Plugin Hub Loop 7 Release Packaging Readiness
doc_type: runbook
module: product_engineering
topic: plugin-hub-loop7-release-packaging
status: draft
created: 2026-07-01
updated: 2026-07-01
owner: self
source: codex
---

# Plugin Hub Loop 7 Release Packaging Readiness

## 1. Scope

Loop 7 prepares a local release package candidate. It does not deploy to production, mutate a remote server, execute a production database backup, call providers, run live platform capture, or submit a Chrome Web Store package.

Decision inherited from Loop 6:

```text
release packaging preparation without production deployment
```

## 2. Evidence Artifacts

| Artifact | Path | Meaning |
| --- | --- | --- |
| Release file inventory JSON | `output/release-packaging/20260701T110015Z/release_file_inventory.json` | Dirty-tree classification for release review. |
| Release file inventory TSV | `output/release-packaging/20260701T110015Z/release_file_inventory.tsv` | Human-readable inventory. |
| API package artifacts | `apps/api/dist/plugin_hub_api-0.1.0.tar.gz`, `apps/api/dist/plugin_hub_api-0.1.0-py3-none-any.whl` | Local Python package build output. |
| Web production build | `apps/web/.next/` | Local Next.js production build output. |
| Extension dist | `apps/extension/dist/amazon`, `apps/extension/dist/reddit`, `apps/extension/dist/instagram` | Local unpacked extension build output. |
| Extension zips | `tmp/outputs/plugin-hub-amazon-voc-0.1.0.zip`, `tmp/outputs/plugin-hub-reddit-voc-0.1.0.zip`, `tmp/outputs/plugin-hub-instagram-voc-0.1.0.zip` | Local extension zip packages. |

## 3. Dirty Tree Inventory

Inventory summary:

| Lane | Count | Release Meaning |
| --- | ---: | --- |
| `include_release_candidate_direct` | 14 | Direct Loop 2/3 release-candidate files. |
| `api_needs_review` | 27 | API changes outside direct Loop 2/3 set; must be reviewed before release branch/package. |
| `web_needs_review` | 9 | Web changes outside direct parser test set; must be reviewed before release branch/package. |
| `extension_or_platform_needs_review` | 36 | Extension/platform changes; package gates passed but still need inclusion decision. |
| `release_infra_review` | 5 | Docker/deploy/env hygiene files; must be reviewed before production proposal. |
| `docs_review` | 4 | Product/strategy/runbook docs. |
| `docs_state` | 2 | `.kiro` / loop state docs. |
| `workspace_hygiene_review` | 2 | Workspace metadata/hygiene files. |
| `evidence_artifact` | 1 | Prior generated evidence. |
| `needs_review` | 1 | Unclassified item requiring manual review. |

Conclusion:

- The direct Loop 2/3 release candidate is small.
- The actual dirty tree is broad.
- A release branch/package should not be cut until all `*_needs_review` and `release_infra_review` items are explicitly included, excluded, or split.

## 4. Local Gate Results

| Gate | Command | Result |
| --- | --- | --- |
| API full tests | `uv --directory apps/api run pytest` | 137 passed, 1 existing Starlette/httpx deprecation warning. |
| API lint | `uv --directory apps/api run ruff check .` | Passed. |
| API typecheck | `uv --directory apps/api run mypy` | Passed; no issues in 26 source files. |
| Web tests | `node_modules/.bin/vitest run` from `apps/web` | 29 passed. |
| Web lint | `node_modules/.bin/eslint app src tests --ext .ts,.tsx` from `apps/web` | Passed. |
| Web typecheck | `node_modules/.bin/tsc --noEmit` from `apps/web` | Passed. |
| Extension tests | `node_modules/.bin/vitest run` from `apps/extension` | 93 passed. |
| Extension lint | `node_modules/.bin/eslint src tests --ext .ts,.tsx` from `apps/extension` | Passed. |
| Extension typecheck | `node_modules/.bin/tsc --noEmit` from `apps/extension` | Passed. |

## 5. Build And Package Results

| Build / Package | Command | Result |
| --- | --- | --- |
| API package | `uv --directory apps/api build` | Built source distribution and wheel. |
| Web production build | `node_modules/.bin/next build` from `apps/web` | Compiled, typed, and generated production build. |
| Amazon extension build | `PLUGIN_HUB_EXTENSION_TARGET=amazon node_modules/.bin/vite build` | Passed; content script size 250150 bytes. |
| Reddit extension build | `PLUGIN_HUB_EXTENSION_TARGET=reddit node_modules/.bin/vite build` | Passed; content script size 251813 bytes. |
| Instagram extension build | `PLUGIN_HUB_EXTENSION_TARGET=instagram node_modules/.bin/vite build` | Passed; content script size 240900 bytes. |
| Extension zip package | `node scripts/package-extension.mjs` | Produced Amazon, Reddit, and Instagram zip/unpacked outputs. |
| Extension package verification | `node scripts/verify-extension-package.mjs` | `ok=true`; each target manifest v3, version 0.1.0, 15 zip entries. |
| Compose syntax | `docker compose -f deploy/tencent-lighthouse/docker-compose.yml config --quiet` | Passed. |

## 6. Evidence Grade Gate

Allowed claim:

- Plugin Hub has a local release packaging candidate with full local gates, local builds, extension packages, and compose syntax proof.

Blocked claims:

- Production is updated.
- Loop 2/3 capabilities are production-observed after release.
- Production database backup or migration was executed.
- Chrome extension was manually loaded in a real browser.
- Amazon/Reddit/Instagram live platform capture was executed.
- Provider calls were executed.

Evidence grade:

```text
L1-local-runtime/build-package
```

Production upgrade still requires:

1. release file inventory review;
2. explicit deploy approval;
3. production DB backup execution approval;
4. deployment record;
5. post-release L3 read-only smoke.

## 7. Release Proposal Boundary

Before a production proposal, decide each inventory lane:

| Lane | Required Decision |
| --- | --- |
| `include_release_candidate_direct` | include or split into a narrow release branch. |
| `api_needs_review` | include with API test coverage or split out. |
| `web_needs_review` | include with Web test/build evidence or split out. |
| `extension_or_platform_needs_review` | include only if extension release is in scope; otherwise split out. |
| `release_infra_review` | include only after deploy operator review. |
| `docs_review` / `docs_state` | include as evidence docs or keep local. |
| `evidence_artifact` | keep as local evidence; do not treat as release source. |

## 8. Next Loop Recommendation

Loop 8 should be:

```text
release branch/file-inventory decision, no production deploy
```

Expected output:

- include/exclude/split decision for every dirty-tree lane;
- a proposed release branch or staging set;
- a deploy approval request packet, if the user wants to proceed;
- no production side effects without explicit approval.

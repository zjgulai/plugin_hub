---
title: Plugin Hub Loop 8 Release Branch Inventory Decision
doc_type: decision_record
module: product_engineering
topic: plugin-hub-loop8-release-branch-inventory
status: draft
created: 2026-07-01
updated: 2026-07-01
owner: self
source: codex
---

# Plugin Hub Loop 8 Release Branch Inventory Decision

## 1. Decision

Choose a **broad app release candidate** rather than a narrow 14-file Loop 2/3 release.

This is a file-inventory decision only:

```text
no git stage / no branch / no commit / no push / no production deploy
```

Reason: the route and product changes are coupled. The original 14 direct Loop 2/3 files are not enough because API route registration, platform settings, CORS, Web platform UI, Extension packaging, deploy files, and test fixtures all participate in the verified local candidate.

## 2. Decision Artifacts

| Artifact | Path |
| --- | --- |
| Source inventory | `output/release-packaging/20260701T110015Z/release_file_inventory.json` |
| File decision JSON | `output/release-branch-decision/20260701T110851Z/release_branch_file_decision.json` |
| File decision TSV | `output/release-branch-decision/20260701T110851Z/release_branch_file_decision.tsv` |
| Loop 7 readiness | `docs/workflows/plugin-hub-loop7-release-packaging-readiness-draft-20260701.md` |

## 3. Decision Summary

| Decision | Count | Meaning |
| --- | ---: | --- |
| `include_broad_app_release_candidate` | 82 | Product source, tests, fixtures, and app-level changes included in the broad candidate. |
| `include_extension_packaging_candidate` | 3 | Extension packaging scripts included with the candidate. |
| `include_release_infra_candidate` | 4 | Docker/deploy/env support files included for release review. |
| `include_release_packet_docs` | 6 | Runbooks and release evidence docs included as release packet docs. |
| `include_workspace_hygiene_candidate` | 1 | Workspace hygiene change included for review. |
| `split_business_analysis_docs` | 2 | Business/strategy analysis split from app release source. |
| `split_diagnostic_tooling` | 1 | Browser diagnostic helper split from app release source. |
| `split_local_planning_state` | 1 | `.kiro` working state split from app source release. |
| `exclude_source_keep_as_local_evidence` | 1 | Generated evidence artifacts kept local, not app source. |

No inventory row remains undecided.

## 4. Included Candidate Groups

### App Source And Tests

Include the API, Web, Extension, and test/fixture changes as one broad candidate.

Rationale:

- `main.py` wires multiple new routes, so API route files cannot be separated safely by endpoint alone.
- Web API parsing and platform workspace changes expect the new API capability shapes.
- Extension packaging and target-specific builds were verified together in Loop 7.
- Full API/Web/Extension local gates passed.

### Release Infra

Include:

- `.dockerignore`
- `.env.example`
- `apps/api/Dockerfile`
- `apps/web/Dockerfile`
- `deploy/tencent-lighthouse/*`

Rationale:

- Docker Compose config passed locally.
- Infra files are needed for a reviewable deploy proposal.
- Inclusion does not authorize production deployment.

### Release Packet Docs

Include the runbooks that explain evidence gates, production read-only smoke, release alignment, path selection, and package readiness.

Rationale:

- The release is evidence-gated and has platform/live-read boundaries.
- Reviewers need docs that explain why local green gates are not production proof.

## 5. Split / Exclude Groups

| Group | Decision | Reason |
| --- | --- | --- |
| Business analysis drafts | Split from app release. | Useful for leadership reporting, but not required for app source release. |
| Browser diagnostic helper | Split from app release. | Support tooling; review separately if needed. |
| `.kiro` planning state | Split from app release. | Active working memory, not app product source by default. |
| `output/` evidence | Exclude from source release; keep local. | Evidence artifacts should be referenced, not treated as source. |

## 6. Evidence Grade

Supported:

- File inventory has an include/split/exclude decision for every dirty entry from Loop 7 inventory.
- The release candidate is ready for a branch/staging proposal.

Not supported:

- Git index has not been staged.
- Release branch has not been created.
- Commit and push have not been performed.
- Production deployment has not been approved or executed.
- Production read-only post-release smoke has not been run.

Evidence grade:

```text
L1-local-file-inventory-decision
```

## 7. Next Loop Recommendation

Loop 9 should prepare a **release approval packet** before any git staging:

1. name the proposed release branch;
2. list included groups and split groups;
3. list last green gates from Loop 7;
4. list source artifacts and local build/package artifacts;
5. list production preflight requirements;
6. ask for explicit approval before staging files or creating a release branch.

Blocked until explicit approval:

- `git add`
- branch creation
- commit
- push
- PR creation
- production DB backup execution
- production deploy
- remote server mutation
- provider calls
- platform live capture

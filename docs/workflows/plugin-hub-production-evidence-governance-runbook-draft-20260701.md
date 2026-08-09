---
title: Plugin Hub Production Evidence Governance Runbook
doc_type: runbook
module: product_engineering
topic: plugin-hub-production-evidence-governance
status: draft
created: 2026-07-01
updated: 2026-08-01
owner: self
source: codex
---

# Plugin Hub Production Evidence Governance Runbook

## 2026-07-10 Adversarial Audit And Deployment Addendum

The July 1 observations and Loop 38 findings below remain historical evidence.
Loop 39 subsequently deployed the authorized authentication, SQLite, backup,
permission, and Nginx hardening and completed production recovery acceptance.

Before making any current durability or security claim, read:

```text
docs/workflows/plugin-hub-loop38-data-asset-adversarial-audit-draft-20260710.md
docs/workflows/plugin-hub-loop39-production-hardening-acceptance-20260710.md
docs/workflows/plugin-hub-loop40-offhost-backup-insight-snapshot-acceptance-20260710.md
```

Loop 39 historical boundary, superseded by the separately authorized Loop 40
state recorded in Section 11:

```text
production hardening deployed / verified backup and restore active
no migration / no provider call / no live capture / no Web Store submission
```

Latest recorded authorized state (historical Loop 40 acceptance, not a fresh
production observation):

```text
production hardening deployed / encrypted off-host backup accepted
explicit 0001_analysis_snapshots migration applied / post-migration baselines recorded
no historical backfill / no provider call / no live capture / no Web Store submission
```

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
| Capture capability | `/api/capture-capabilities` | 200 | `capture-capabilities.body` | The sampled 2026-07-01 production response exposed capability inventory without Loop 3 evidence-label fields. |
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
- Do not infer authorized Instagram Graph live-read readiness; the sampled 2026-07-01 response reported the Graph path as credential-gated.
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

## 7. Historical Pre-Loop40 Database Upgrade Boundary

This section preserves the database boundary used before Loop 40. Loop 40 later
introduced the explicit `0001_analysis_snapshots` migration runner described in
Section 11. The facts and gates below remain the historical approval contract;
they are not the current schema-status statement.

Facts recorded before Loop 40:

- Local API defaults to `sqlite+pysqlite:///./plugin_hub.db`.
- Production compose sets the API and worker database URL to `sqlite+pysqlite:////data/plugin_hub.db`.
- Production compose mounts `/opt/plugin-hub/data` into `/data`.
- API startup calls SQLAlchemy `Base.metadata.create_all(bind=engine)`.
- No Alembic or equivalent migration framework was configured at that point.

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

## 8. Historical Next Value Step After The 2026-07-01 Smoke

This list records the next step proposed after the July 1 read-only smoke. Later
Loop 39 and Loop 40 acceptances supersede it where their dated evidence applies.

To raise the evidence grade for Loop 2 and Loop 3 work:

1. Deploy the local API/Web changes through the approved release path.
2. Re-run this production read-only smoke.
3. Confirm `/api/insights/voc-signals` returns 200 in production.
4. Confirm `/api/capture-capabilities` includes evidence-label fields in production.
5. Keep Instagram Graph live-read blocked until platform rights, backend-only credential configuration, and explicit live-read approval are present.

## 9. 2026-07-10 Loop 38-39 Historical Hardening Addendum

Before any future durability or security claim, read the Loop 38 adversarial
audit first. The Loop 38 local candidate provided API authentication, SQLite
FK/WAL/busy-timeout parity for API and worker, idempotent extension ingestion,
payload-hash verification, bounded reads, run-level asset history, verified
online backups, and SSRF target validation.

The following list was the Loop 38 deployment gate. At the Loop 39 acceptance
point, separate authorization had completed items 1-6; item 7 remained partially
open because the timer was active but no off-host retention lane existed. Loop
40 later closed that remaining action as recorded in Section 11:

1. create independent API read/write keys and dashboard Basic Auth without printing values;
2. set `/opt/plugin-hub/data` and `/opt/plugin-hub/backups` to service-owned `0700`;
3. set DB/WAL/SHM/backup/manifest files to `0600` and verify owner/group;
4. create and restore a verified online backup before changing journal mode;
5. prove API and worker both report WAL, FK enabled, FULL synchronous, and the configured busy timeout;
6. prove anonymous dashboard/API access is denied before enabling plugin writes;
7. install and observe the backup timer, then create an off-host retention lane.

At the Loop 39 acceptance point, derived insight history remained blocked on an
append-only snapshot migration. Loop 40 later introduced the explicit migration
and post-migration baseline snapshots described in Section 11. Pre-migration
read-time output still cannot be represented as historical persistence.

## 10. 2026-07-10 Loop 39 Authorized Hardening State

Production evidence recorded at the Loop 39 acceptance point:

- dashboard and API anonymous access return 401; Basic Auth/read-key access return 200;
- all 19 API operations are protected and Nginx rate limiting is active;
- API and worker use WAL, FK enabled, FULL synchronous, and 15000ms busy timeout;
- data/backup directories are 0700; DB, backup, manifest, lock, and runtime env are 0600;
- daily systemd backup timer is enabled and active with verified retention count 14;
- latest accepted backup is `plugin_hub_20260710T121013Z.db`, with matching manifest/hash and 7/402/402 counts;
- no-network isolated API restore passed with `quick_check=ok` and zero FK issue;
- production raw/canonical history remained 7/402/402 with 402/402 payload hashes matching.

Future release checks must use authenticated requests. Do not revert to the
historical public GET-only checklist without explicitly labeling the expected
401 response.

## 11. 2026-07-10 Off-Host And Insight Snapshot State

This is the latest accepted production state recorded in this runbook. It is
historical L4 evidence, not a fresh observation of current production. Any new
claim about current production requires a fresh L3 read-only check or a newly
authorized L4 action, depending on the claim.

Loop 40 received separate authorization and completed both remaining data-asset
actions from Loop 39:

- the production backup is pulled to this Mac as an age-encrypted archive after
  remote manifest/hash/integrity validation;
- the age identity is stored in Keychain and the recipient public key is kept in
  the local Plugin Hub config;
- `com.pray.plugin-hub-offhost-backup` runs daily at 04:15 and retains 30
  encrypted archives;
- migration `0001_analysis_snapshots` explicitly creates `analysis_runs` and
  `analysis_artifact_snapshots`; startup `create_all` does not create them;
- database triggers reject UPDATE and DELETE on both snapshot tables;
- production has one Amazon and one Reddit baseline run created after migration,
  with 824 immutable artifacts and zero digest mismatch;
- the post-migration production and off-host backup is
  `plugin_hub_20260710T130106Z.db` / `.tar.age` and passed no-network API restore.

The Mac target is a second host, not a cross-region/object-storage guarantee.
The LaunchAgent also depends on the user session, SSH alias, and Keychain being
available. A later durability step should add monitored object storage without
removing the verified local encrypted copy recorded by Loop 40.

No snapshot row represents output from before its recorded `created_at`.
Historical pre-migration insight output remains unknown and must never be
reconstructed and relabeled as an original past result.

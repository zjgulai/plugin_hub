---
title: Plugin Hub Core Evidence Break-glass Runbook
doc_type: runbook
module: api_persistence
topic: core-evidence-emergency-repair
status: draft
created: 2026-08-09
updated: 2026-08-09
owner: self
source: human+ai
---

# Plugin Hub Core Evidence Break-glass Runbook

## 1. Purpose and authorization boundary

This runbook defines the exceptional process for repairing an already persisted
`raw_source_items` or `canonical_voc_units` row after
`0004_core_evidence_immutability` has been applied. It is not authorization to
run a repair, inspect production payloads, stop a service, copy a database,
create a backup, deploy code, restart a writer, or change production data.

Each use requires a separate approval naming all of the following:

- incident or change identifier;
- accountable operator and approver;
- exact environment, database path, release SHA, and migration versions;
- exact table and primary-key allowlist, expressed as counts and identifiers in
  the private change record rather than in shared logs;
- reviewed replacement SQL and expected before/after digests;
- maintenance window, rollback owner, and maximum lock duration;
- pre-repair and post-repair backup destinations and retention class.

Absence or ambiguity in any field is a stop condition. Approval for a migration,
deployment, backup, or read-only inspection does not imply approval for this
break-glass procedure.

## 2. Invariants

- Raw evidence remains append-only during normal operation.
- Do not delete, rewrite, or deduplicate evidence as part of application
  deployment.
- Do not modify `schema_migrations` during a repair.
- Do not disable foreign keys, switch journal mode, or use `PRAGMA
  writable_schema`.
- Drop and restore only the six triggers owned by
  `0004_core_evidence_immutability`.
- Perform the approved row change and guard restoration in one
  `BEGIN IMMEDIATE` transaction. Any failed assertion causes `ROLLBACK`.
- A successful collection still writes `collection_runs`, `raw_source_items`,
  and `canonical_voc_units` in one application transaction.
- Do not print payloads, source URLs, authors, bodies, credentials, or private
  backup paths into shared receipts.

## 3. Required preflight evidence

Record a private, timestamped receipt containing:

1. host and service identity, database inode/device, file size, owner/mode, and
   release SHA;
2. `migration status` output showing `0003_core_evidence_baseline` and
   `0004_core_evidence_immutability` as applied and contract-verified;
3. proof that API, worker, scheduled jobs, extension ingestion, and every other
   writer are stopped, followed by a second observation covering the agreed
   quiet interval;
4. database `quick_check=ok`, zero `foreign_key_check` rows, table counts, and
   sanitized aggregate digests;
5. all six expected trigger names and their normalized definitions;
6. a verified online pre-repair backup, manifest, SHA-256, permissions, and an
   isolated restore proof;
7. a completed rehearsal of the exact reviewed repair against that isolated
   restore, including expected affected-row count, counts, digests, integrity,
   and trigger restoration.

The status command is read-only:

```text
uv --directory apps/api run python -m plugin_hub_api.migration_cli status \
  --database-url <approved-sqlite-url>
```

Do not run `migration down` for a repair. Populated core evidence deliberately
blocks ordinary rollback with `core_evidence_rows_exist`.

## 4. Exact repair transaction template

The reviewed operator tool must enable fail-on-error behavior and execute the
following as one connection and one transaction. Replace only the marked repair
statement and its bound allowlist. Never interpolate identifiers from shell
input.

```sql
BEGIN IMMEDIATE;

DROP TRIGGER raw_source_items_no_update;
DROP TRIGGER raw_source_items_no_delete;
DROP TRIGGER raw_source_items_no_replace;
DROP TRIGGER canonical_voc_units_no_update;
DROP TRIGGER canonical_voc_units_no_delete;
DROP TRIGGER canonical_voc_units_no_replace;

-- Execute the separately reviewed, parameter-bound repair statement here.
-- It must target only the approved table and primary-key allowlist.
-- Assert that the affected-row count exactly equals the approved count.

CREATE TRIGGER raw_source_items_no_update
BEFORE UPDATE ON raw_source_items
BEGIN
    SELECT RAISE(ABORT, 'raw_source_items_append_only');
END;

CREATE TRIGGER raw_source_items_no_delete
BEFORE DELETE ON raw_source_items
BEGIN
    SELECT RAISE(ABORT, 'raw_source_items_append_only');
END;

CREATE TRIGGER raw_source_items_no_replace
BEFORE INSERT ON raw_source_items
WHEN EXISTS (
    SELECT 1 FROM raw_source_items
    WHERE id = NEW.id
       OR (
            collection_run_id = NEW.collection_run_id
            AND source_kind = NEW.source_kind
            AND source_object_id = NEW.source_object_id
       )
)
BEGIN
    SELECT RAISE(ABORT, 'raw_source_items_append_only');
END;

CREATE TRIGGER canonical_voc_units_no_update
BEFORE UPDATE ON canonical_voc_units
BEGIN
    SELECT RAISE(ABORT, 'canonical_voc_units_append_only');
END;

CREATE TRIGGER canonical_voc_units_no_delete
BEFORE DELETE ON canonical_voc_units
BEGIN
    SELECT RAISE(ABORT, 'canonical_voc_units_append_only');
END;

CREATE TRIGGER canonical_voc_units_no_replace
BEFORE INSERT ON canonical_voc_units
WHEN EXISTS (
    SELECT 1 FROM canonical_voc_units
    WHERE id = NEW.id
       OR (
            collection_run_id = NEW.collection_run_id
            AND source_kind = NEW.source_kind
            AND source_object_id = NEW.source_object_id
       )
)
BEGIN
    SELECT RAISE(ABORT, 'canonical_voc_units_append_only');
END;

-- Before COMMIT, the operator tool must assert all of the following:
-- 1. exactly six expected guard names exist;
-- 2. normalized guard SQL equals the reviewed 0004 definitions;
-- 3. both run-scoped unique indexes exist and are unique;
-- 4. affected-row count, target digest, and table counts match expectations;
-- 5. PRAGMA foreign_key_check returns zero rows.

COMMIT;
```

If the repair tool cannot enforce the assertions before `COMMIT`, it is not an
approved tool for this procedure. A missing trigger, unexpected row count,
digest mismatch, uniqueness failure, lock timeout, SQL error, or operator
uncertainty requires `ROLLBACK` and incident escalation.

## 5. Post-transaction verification

With writers still stopped:

1. run read-only migration status and require both core contracts to verify;
2. require `quick_check=ok` and zero foreign-key issues;
3. compare table counts and sanitized aggregate digests with the approved
   before/after expectations;
4. probe UPDATE, DELETE, and `INSERT OR REPLACE` on an isolated post-repair copy,
   not on the live database, and require append-only rejection;
5. create and verify the approved post-repair backup and isolated restore;
6. record trigger definitions, migration checksums, backup hash, affected-row
   count, verification results, elapsed lock time, operator, and approver.

Only after those checks pass may the separately authorized restart occur.
Restart writers one class at a time, verify health, then perform only the
approved read-only API smoke. Do not perform a live collection or provider call
unless that side effect has its own approval.

## 6. Abort and restore conditions

Abort before mutation if identity, writer shutdown, backup restore, schema
contract, allowlist, or rehearsal evidence is incomplete. Roll back the open
transaction on any in-transaction mismatch.

If a commit completed but post-verification fails, keep writers stopped and
escalate. Restoring the pre-repair backup is a separate destructive production
action and requires explicit authorization. Never attempt an improvised second
repair or edit the migration ledger to hide drift.

## 7. Evidence grade and claims

Writing or testing this document is at most local documentation evidence. An
isolated rehearsal is fixture/copy evidence. Only a separately authorized live
receipt can support the narrow claim that the listed rows were repaired and all
guards were restored. None of those receipts proves unrelated historical data,
provider, capture, deployment, or product behavior.

---
title: Plugin Hub Core Evidence Migration Design
doc_type: design_spec
module: api_persistence
topic: core-evidence-baseline-and-immutability
status: review-ready
created: 2026-08-09
updated: 2026-08-09
owner: self
source: human+ai
---

# Plugin Hub Core Evidence Migration Design

## 1. Decision

Implement `T02-01/T02-02` as two additive migrations in the existing Plugin Hub
migration runner:

1. `0003_core_evidence_baseline` takes explicit ownership of the
   `collection_runs`, `raw_source_items`, and `canonical_voc_units` schema and
   adds run-scoped uniqueness.
2. `0004_core_evidence_immutability` makes raw and canonical evidence
   append-only at the SQLite boundary and blocks replacement-style overwrite.

This batch uses only fresh temporary SQLite databases and synthetic populated
fixtures. It does not read, decrypt, copy, migrate, or write a production
database. Production-copy rehearsal, production migration, deployment, backup
execution, and runtime changes remain separate approval gates.

## 2. Context

The accepted source baseline is remote `main` commit
`1a4152ed7834303acb772196dd2866ed2e886af4`.

The current implementation already has a small explicit migration runner:

- `schema_migrations` records version, SQL checksum, and applied time;
- unknown applied versions fail closed;
- checksum drift fails closed;
- SQLite DDL runs inside `BEGIN IMMEDIATE`;
- `0001_analysis_snapshots` and `0002_analysis_snapshot_insert_guards` own the
  snapshot tables and append-only guards;
- application startup does not apply those migrations automatically.

The unresolved core-evidence gap is different:

- `Base.metadata.create_all()` still creates the three core evidence tables;
- their schema is not owned by an explicit migration;
- raw and canonical rows have no database-level UPDATE/DELETE protection;
- run-scoped source identity is checked by request validation but not enforced
  by a database unique index;
- a future direct SQL writer could bypass repository conventions.

The collection invariant remains non-negotiable: one successful collection
writes the parent run, raw rows, and canonical rows in one repository
transaction.

## 3. Goals

- Make the three core evidence tables reproducible from explicit migration SQL.
- Preserve the existing migration checksums for `0001` and `0002` exactly.
- Refuse unknown migration versions, checksum drift, partial legacy schema, and
  duplicate run-scoped source identities before reporting success.
- Enforce one raw and one canonical identity per
  `(collection_run_id, source_kind, source_object_id)`.
- Reject raw/canonical UPDATE, DELETE, and replacement-style overwrite in the
  database, without blocking normal append operations.
- Keep empty-database migration and empty-database rollback deterministic.
- Block ordinary rollback when core evidence exists.
- Document an auditable, restore-first break-glass process without executing it.
- Preserve all current repository transaction, idempotency, snapshot, backup,
  authentication, and API behavior.

## 4. Non-goals

- No Alembic adoption or general migration-framework replacement.
- No production or copied-production database access.
- No production migration, deployment, restart, backup, restore, or timer work.
- No data cleanup, deduplication, historical backfill, or evidence rewrite.
- No new API route, Web/Extension behavior, actor model, or provider call.
- No change to snapshot history semantics or pre-migration history claims.
- No automatic migration during API or worker startup.

## 5. Considered Approaches

### 5.1 Selected: two additive migrations

Separating baseline ownership from immutability keeps each concern independently
reviewable. The baseline can prove schema and uniqueness before mutation guards
are installed, while the guard migration can be rolled back on an empty test
database without changing the baseline contract.

### 5.2 Rejected: one combined migration

A combined migration is shorter but couples table ownership, duplicate checks,
indexes, and six guards into one rollback and one failure surface. It makes it
harder to distinguish schema drift from immutability defects.

### 5.3 Rejected: introduce Alembic

Alembic would provide a mature migration ecosystem, but it would add a second
framework, configuration, dependency, and operational contract to a narrowly
scoped SQLite hardening batch. The existing runner already supplies the needed
ordering, checksums, unknown-version refusal, and transactional DDL.

## 6. Architecture

### 6.1 Migration contract extension

Extend the existing `Migration` definition without changing legacy checksums.
New migrations may carry a deterministic schema-contract payload and validation
hook. When no contract payload is present, checksum calculation remains byte-for-
byte identical to the current algorithm, preserving the accepted `0001` and
`0002` checksums.

For a migration with a schema contract, the checksum covers both:

- ordered `up_statements`; and
- the normalized contract describing required tables, columns, foreign keys,
  indexes, and triggers.

Validation runs inside the same migration transaction. A failed precondition or
postcondition rolls back all DDL and the `schema_migrations` insert.

Both `migration up` and read-only `migration status` validate the contract for
every applied migration that defines one. Status therefore fails closed if a
recorded core index or guard is missing instead of reporting only that the
version row exists. SQLite status keeps its current read-only connection and
must not enable WAL or create a missing database file.

### 6.2 `0003_core_evidence_baseline`

The migration explicitly defines the current SQLite schema for:

- `collection_runs`;
- `raw_source_items`;
- `canonical_voc_units`.

Behavior by starting state:

- **Fresh database:** create all three tables, their existing indexes and
  foreign keys, then create the two run-scoped unique indexes.
- **Compatible legacy database:** validate required tables, columns, nullability,
  primary keys, and child-to-run foreign keys before creating unique indexes.
- **Partial or incompatible database:** fail closed without recording `0003`.
- **Already migrated database:** validate the recorded checksum and return no
  changed version.

The unique indexes are:

- raw: `(collection_run_id, source_kind, source_object_id)`;
- canonical: `(collection_run_id, source_kind, source_object_id)`.

Before either index is created, the migration counts duplicate groups. Any
duplicate causes a sanitized `core_evidence_duplicate_identity` failure. Error
output reports the table and group count, not payload, source URL, author, body,
or source object identifier.

After `0003`, normal runtime initialization no longer creates the three core
tables. `create_all` remains limited to the operational tables that have not yet
entered the explicit migration system. A fresh environment must run the explicit
migration command before API or worker use; missing core schema fails closed.

### 6.3 `0004_core_evidence_immutability`

Install six guards:

- `raw_source_items_no_update`;
- `raw_source_items_no_delete`;
- `raw_source_items_no_replace`;
- `canonical_voc_units_no_update`;
- `canonical_voc_units_no_delete`;
- `canonical_voc_units_no_replace`.

The four UPDATE/DELETE triggers implement the requested immutability boundary.
The two INSERT guards close SQLite `INSERT OR REPLACE` overwrite behavior, which
can otherwise bypass a simple UPDATE/DELETE-only design depending on recursive
trigger settings. They reject an insert when either the primary key or the
run-scoped evidence identity already exists.

New evidence identities remain insertable. The repository continues to insert
the run, raw rows, and canonical rows and commit them once. No normal collection
path needs UPDATE, DELETE, or REPLACE on evidence rows.

### 6.4 Runtime initialization

`init_database()` will use an explicit table allowlist for non-migrated
operational tables. Core evidence tables are excluded from `create_all`.

The API and worker do not run migrations automatically. If an operator starts a
fresh runtime before `migration up`, requests that require core evidence fail
because the schema is absent. This is deliberate: startup must not silently
promote schema state.

Tests that require the complete application schema will explicitly run pending
migrations during fixture setup. Tests for missing-migration behavior will opt
out and assert fail-closed results.

### 6.5 Rollback rules

Rollback remains safe by default:

- `0004 down` is allowed only when both evidence child tables are empty;
- `0003 down` is allowed only when all three core tables are empty;
- when evidence exists, the runner raises
  `core_evidence_rows_exist` and makes no schema change;
- rollback never deletes or rewrites evidence to make itself succeed.

On an empty test database, `0004 down` removes its six triggers and `0003 down`
removes its indexes and core tables in dependency-safe order.

### 6.6 Break-glass runbook

Add
`docs/workflows/plugin-hub-core-evidence-break-glass-runbook-draft-20260809.md`.
It defines a separate, explicitly authorized emergency process:

1. record incident identifier, owner, exact database path, release SHA, reason,
   approved row scope, and maintenance window;
2. stop all writers and prove they are stopped;
3. create and verify an online backup, manifest, SHA-256, counts, quick check,
   and foreign-key check;
4. rehearse the exact repair on an isolated copy;
5. in one explicit `BEGIN IMMEDIATE` transaction, drop only the six named
   guards, perform only the approved row repair, recreate the exact checked-in
   guard SQL, validate the repaired rows and guards, and only then commit;
6. verify trigger definitions, migration checksums, counts, hashes,
   `quick_check`, foreign keys, and affected rows;
7. create and verify a post-repair backup and record the complete receipt;
8. restart writers and perform separately approved read-only validation.

The runbook is documentation, not authorization. This batch neither rehearses
against a production copy nor performs a live break-glass action.

## 7. Data Flow

### 7.1 Fresh local database

```text
migration up
  -> create schema_migrations
  -> apply 0001 and 0002
  -> 0003 creates and validates core evidence schema + unique indexes
  -> 0004 creates and validates append-only guards
  -> record checksums
  -> application startup creates only remaining operational tables
```

### 7.2 Compatible populated synthetic database

```text
legacy create_all schema + synthetic run/raw/canonical rows
  -> migration preflight checks table contract and duplicate groups
  -> 0003 adds unique indexes without changing rows
  -> 0004 adds guards without changing rows
  -> postflight compares counts and stable row digests
```

### 7.3 Normal collection write

```text
validate request and idempotency
  -> insert collection_run
  -> insert raw_source_items
  -> insert canonical_voc_units
  -> commit once
```

Any failure, including a uniqueness or guard violation, rolls back the entire
repository transaction.

## 8. Error Contract

Expected fail-closed errors use stable, non-sensitive codes:

- `unknown_migration_versions:<versions>`;
- `migration_checksum_mismatch:<version>`;
- `core_evidence_schema_partial`;
- `core_evidence_schema_mismatch:<table>`;
- `core_evidence_duplicate_identity:<table>:<group_count>`;
- `core_evidence_rows_exist`;
- `raw_source_items_append_only`;
- `canonical_voc_units_append_only`.

No error includes raw payload, body, author, source URL, credential, or source
object identifier.

## 9. Implementation Scope

Expected source changes:

- `apps/api/src/plugin_hub_api/migrations.py`;
- `apps/api/src/plugin_hub_api/db.py`;
- `apps/api/src/plugin_hub_api/migration_cli.py` so read-only status validates
  and reports applied schema contracts without enabling WAL;
- `apps/api/tests/conftest.py` for explicit migrated-schema fixtures;
- a focused core-evidence migration test module;
- the break-glass runbook named above.

Existing snapshot migrations, application routes, schemas, repository public
methods, Web, Extension, deployment templates, and production scripts stay out
of scope unless a failing regression proves a direct dependency.

## 10. Verification Strategy

### 10.1 Migration tests

- Legacy `0001` checksum remains exactly unchanged.
- Empty database `up` applies all versions and a second `up` changes nothing.
- Fresh schema exists only after explicit migration.
- Compatible synthetic populated schema upgrades without row/count/digest drift.
- Partial or incompatible schema is refused atomically.
- Duplicate raw or canonical identity is refused atomically.
- Unknown version and checksum drift are refused before new DDL is recorded.
- Empty rollback removes `0004` then `0003` in order.
- Populated rollback is blocked without deleting or changing rows.

### 10.2 Immutability tests

- raw UPDATE and DELETE are rejected;
- canonical UPDATE and DELETE are rejected;
- raw and canonical `INSERT OR REPLACE` overwrite attempts are rejected;
- new distinct raw and canonical identities remain insertable;
- trigger names and normalized SQL match the migration contract.

### 10.3 Repository regression

- successful collection still writes one run, matching raw rows, and matching
  canonical rows in one transaction;
- duplicate identity rolls back the parent and both child sets;
- task-fenced collection commit keeps its existing ownership semantics;
- current snapshot migration/API tests remain green.

### 10.4 Full local gates

- frozen API dependency sync;
- focused migration, collection, database-hardening, snapshot, and dry-run tests;
- full API pytest;
- ruff, mypy, and package build;
- `git diff --check`;
- lightweight secret scan over the exact changed files.

All database fixtures live under temporary test directories. No command may
reference production SSH aliases, Keychain entries, `/opt/plugin-hub`, encrypted
off-host archives, or historical production database filenames.

## 11. Acceptance Criteria

The local batch is complete only when:

1. `0003` and `0004` are deterministic and idempotent.
2. Existing `0001/0002` checksum compatibility is preserved.
3. Fresh and populated synthetic databases pass migration and integrity checks.
4. Run-scoped raw/canonical uniqueness is database-enforced.
5. UPDATE, DELETE, and replacement overwrite are database-rejected.
6. Normal transactional collection writes still pass.
7. Populated rollback fails closed and preserves every evidence row.
8. The break-glass runbook contains exact approval, backup, rehearsal,
   transaction, verification, and receipt requirements.
9. Full local API quality gates pass.
10. The evidence claim remains `L2 fixture/local migration proof`; no production
    readiness, copied-production rehearsal, deployment, or live migration claim
    is made.

## 12. Follow-on Gates

After local implementation and independent review, later gates remain separate:

1. exact file staging and local atomic commit;
2. push and Draft PR;
3. PR review, CI, Ready, and exact-head merge;
4. authorized copied-production migration rehearsal with backup/restore proof;
5. authorized production migration and post-migration read-only validation;
6. deployment, if application runtime changes require it.

None of these follow-on actions is authorized by this design.

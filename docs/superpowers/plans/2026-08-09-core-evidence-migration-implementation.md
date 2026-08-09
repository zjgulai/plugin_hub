---
title: Plugin Hub Core Evidence Migration Implementation Plan
doc_type: implementation_plan
module: api_persistence
topic: core-evidence-baseline-and-immutability
status: completed
created: 2026-08-09
updated: 2026-08-09
owner: self
source: human+ai
design: docs/superpowers/specs/2026-08-09-core-evidence-migration-design.md
---

# Plugin Hub Core Evidence Migration Implementation Plan

## Boundary

Implement and verify `T02-01/T02-02` only on temporary SQLite databases with
synthetic fixtures. Do not access a production copy, production host, backup,
Keychain credential, deployment runtime, provider, Store, or live capture path.
Do not push, open a PR, merge, or deploy in this gate.

Maximum evidence grade: `L2 fixture/local migration proof`.

## Task 1: Establish failing core migration contracts

Files:

- add `apps/api/tests/test_core_evidence_migrations.py`;
- update snapshot migration expectations only where the global ordered version
  list legitimately grows.

Tests:

1. `0001` and `0002` accepted checksums stay unchanged.
2. A raw empty SQLite file gains all four migration versions and all three core
   tables only through explicit `up`.
3. Second `up` is idempotent and read-only `status` validates contracts.
4. Existing compatible SQLAlchemy-created core tables upgrade without count or
   stable-row-digest drift.
5. A partial core schema fails atomically with no `0003` row.
6. Duplicate raw/canonical run-scoped identities fail atomically without
   leaking identifiers.
7. Missing unique indexes or guards after an applied migration make status fail
   closed.
8. Populated rollback is blocked; empty rollback removes `0004` then `0003`.
9. UPDATE, DELETE, and `INSERT OR REPLACE` are rejected for both evidence tables.
10. A distinct append remains allowed.

Run the focused test module and retain its initial failure as the TDD red gate.

## Task 2: Extend the migration contract safely

File: `apps/api/src/plugin_hub_api/migrations.py`.

Changes:

- add the `0003` and `0004` version constants;
- allow new migrations to include a normalized contract payload and validators;
- preserve legacy checksum calculation when no contract payload exists;
- validate applied migration contracts during `up` and engine-based status;
- add sanitized schema/duplicate/contract errors;
- add migration-specific rollback guards;
- keep all SQLite validation and DDL in the existing `BEGIN IMMEDIATE`
  transaction.

No existing migration SQL may be reformatted or otherwise changed.

## Task 3: Implement `0003_core_evidence_baseline`

File: `apps/api/src/plugin_hub_api/migrations.py`.

Changes:

- define explicit current SQLite DDL for `collection_runs`,
  `raw_source_items`, and `canonical_voc_units`;
- preserve the current columns, nullability, primary keys, child foreign keys,
  and existing indexes;
- validate all-or-none legacy table presence and required schema shape;
- count duplicate groups before adding unique indexes;
- add unique indexes on
  `(collection_run_id, source_kind, source_object_id)` for raw and canonical;
- post-validate tables, indexes, and foreign keys;
- define empty-only down statements in dependency-safe order.

## Task 4: Implement `0004_core_evidence_immutability`

File: `apps/api/src/plugin_hub_api/migrations.py`.

Changes:

- add raw/canonical UPDATE and DELETE abort triggers;
- add raw/canonical INSERT guards for primary-key and run-scoped-identity
  replacement attempts;
- post-validate the six names and normalized trigger SQL;
- block down when either evidence child table contains rows;
- allow empty-database down to remove only these six guards.

## Task 5: Transfer fresh-schema ownership

Files:

- `apps/api/src/plugin_hub_api/db.py`;
- `apps/api/tests/conftest.py`;
- direct database tests that intentionally need a fully migrated schema.

Changes:

- exclude the three migrated core tables from runtime `create_all`;
- keep non-migrated operational tables on the existing initialization path;
- make complete application test fixtures apply explicit migrations before
  exercising evidence routes;
- keep dedicated legacy-schema fixtures able to create the pre-migration core
  layout for upgrade tests;
- do not auto-run migrations in API or worker startup.

## Task 6: Add read-only status contract validation

File: `apps/api/src/plugin_hub_api/migration_cli.py`.

Changes:

- keep SQLite status `mode=ro`, `query_only=ON`, and connection-close behavior;
- refuse missing databases without creating a file;
- after checksum validation, inspect `sqlite_master`, table metadata, foreign
  keys, indexes, and triggers for applied contract migrations;
- report verified contract versions without exposing schema payload values or
  evidence identifiers;
- do not enable WAL or take a write lock for status.

## Task 7: Write the break-glass runbook

File:

- add
  `docs/workflows/plugin-hub-core-evidence-break-glass-runbook-draft-20260809.md`.

The runbook must include authorization, writer shutdown proof, pre-backup,
isolated rehearsal, exact row scope, one `BEGIN IMMEDIATE` repair transaction,
temporary removal and in-transaction restoration of only the six guards,
post-verification, post-backup, restart, read-only smoke, receipts, abort
conditions, and explicit non-authorization language.

## Task 8: Focused verification

Run from `apps/api` with the repository environment:

```text
pytest tests/test_core_evidence_migrations.py -q
pytest tests/test_snapshot_migrations.py tests/test_migration_dry_run_script.py -q
pytest tests/test_collection_runs_api.py tests/test_collection_tasks_api.py -q
pytest tests/test_database_hardening.py tests/test_insight_snapshots_api.py -q
```

Required results:

- no legacy checksum drift;
- no row/count/digest drift on synthetic populated upgrade;
- mutation and replacement probes rejected;
- repository transaction and task fencing remain intact.

## Task 9: Full local quality gates

Run:

```text
uv sync --frozen --all-groups
uv run pytest
uv run ruff check src tests
uv run mypy src
uv build
git diff --check
```

Then inspect exact changed files, run a lightweight secret scan, and confirm the
isolated worktree contains no database, WAL/SHM, backup, credential, cache, or
generated package artifact intended for source control.

## Task 10: Review and handoff

- review the full diff for transaction, rollback, compatibility, and sensitive
  output risks;
- record supported and forbidden evidence claims;
- update local `.kiro` continuity only outside the tracked implementation diff;
- leave implementation changes unstaged and unpushed for a separate exact-file
  staging/commit gate.

## Completion Evidence

- TDD red gates reproduced missing migrations, incomplete foreign-key/index
  validation, rollback rehearsal drift, missing contract validators, and hidden
  table constraints before each fix.
- Python 3.12 full API suite: `268 passed`; Ruff and Mypy passed; source and
  wheel builds completed; `git diff --check` passed.
- Codex review findings were reproduced where valid, fixed with regression
  coverage, and closed with no remaining accepted/actionable finding.
- Evidence remains `L2 fixture/local migration proof`. No production database,
  production copy, backup, deployment, provider, staging, commit, push, or PR
  mutation was performed by this implementation gate.

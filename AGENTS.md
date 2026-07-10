# Plugin Hub Project Guidance

Before changing backend persistence, API security, deployment, backup, or insight history, read:

- `docs/workflows/plugin-hub-loop38-data-asset-adversarial-audit-draft-20260710.md`
- `docs/workflows/plugin-hub-loop39-production-hardening-acceptance-20260710.md`
- `docs/workflows/plugin-hub-loop40-offhost-backup-insight-snapshot-acceptance-20260710.md`
- `docs/workflows/plugin-hub-loop42-pr-review-ci-plan-draft-20260710.md`
- `docs/workflows/plugin-hub-production-evidence-governance-runbook-draft-20260701.md`

Preserve these project invariants:

- A successful collection writes `collection_runs`, `raw_source_items`, and
  `canonical_voc_units` in one transaction.
- Raw evidence is append-only. Do not delete or rewrite production evidence as
  part of application deployment.
- Production database writes, migrations, backup execution, timer installation,
  credential rollout, Nginx reload, and deployment require separate approval.
- Local tests, fixture proof, production read-only evidence, and authorized live
  side effects are different evidence grades and must be reported separately.
- Derived insight history exists only for rows created through the explicit
  `0001_analysis_snapshots` migration and snapshot API. Do not describe
  read-time generation or pre-migration recomputation as historical persistence.

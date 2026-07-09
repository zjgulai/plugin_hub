---
title: Plugin Hub Instagram Graph Authorization Runbook
doc_type: workflow_runbook
module: platform_extensions
topic: instagram-graph-authorization-gate
status: draft
created: 2026-06-21
updated: 2026-06-21
owner: self
source: human+ai
---

# Plugin Hub Instagram Graph Authorization Runbook

## Boundary

This runbook covers the authorization gate before Instagram live capture.

Current implementation is `fixture/local` plus a token-gated Graph client skeleton. It does not configure a real Meta access token, call Meta Graph live endpoints, perform live writes, or write production VOC data.

## Required Inputs

- A Meta app with approved permissions for the target Instagram professional account.
- A backend-only `PLUGIN_HUB_INSTAGRAM_GRAPH_ACCESS_TOKEN`.
- `PLUGIN_HUB_INSTAGRAM_GRAPH_LIVE_READ_ENABLED=true` in the backend runtime.
- A valid Instagram Graph `media_id` supplied in the collection task context.
- A task-level authorization record in the collection task context.
- Explicit approval before any authorized live read-only test.
- Separate explicit approval before any authorized write into a production Plugin Hub backend.

## Readiness Check

Use the backend readiness endpoint:

```bash
curl http://127.0.0.1:8000/api/capture-capabilities
```

Expected default state without a token:

- `server_instagram_fixture_payload`: `fixture_only`
- `server_instagram_graph_comments`: `credential_missing`
- `live_read_enabled`: `false`
- `live_write_enabled`: `false`

Expected state after a backend token is configured but live read is still closed:

- `server_instagram_graph_comments`: `live_read_blocked`
- `configured`: `true`
- `live_read_enabled`: `false`
- `live_write_enabled`: `false`

Expected state after a backend token and live-read switch are configured:

- `server_instagram_graph_comments`: `task_authorization_required`
- `configured`: `true`
- `live_read_enabled`: `true`
- `live_write_enabled`: `false`

The endpoint must never return token values.

Readiness responses include:

- `evidence_grade`: readiness observation stays `L1-public-or-runtime`; fixture-only paths stay `L2-fixture-or-dry-run`.
- `next_required_action`: the smallest next gate to clear, such as configuring a backend-only token after rights confirmation, enabling the live-read switch after approval, or submitting task authorization context to preflight.
- `side_effect_boundary`: confirms `/api/capture-capabilities` is read-only and does not start capture, call Meta Graph, or write production data.

## Authorization Context Preflight

Before creating or running a Graph collection task, validate the task context without
calling Meta Graph:

```bash
curl -X POST http://127.0.0.1:8000/api/capture-authorizations/instagram-graph-live-read/preflight \
  -H 'Content-Type: application/json' \
  -d '{
    "context": {
      "media_id": "17900000000000001",
      "authorization_scope": "instagram_graph_live_read",
      "authorized_by": "reviewer-name-or-ticket",
      "authorized_at": "2026-06-21T00:00:00Z",
      "environment": "local",
      "production_write": false
    }
  }'
```

The preflight response reports:

- `configured`: whether the backend has a configured Graph fetcher.
- `live_read_enabled`: whether the backend live-read switch is open and a fetcher is configured.
- `task_authorization_ready`: whether the submitted context has the required authorization fields.
- `ready_for_worker`: whether the worker would be allowed to reach the Graph fetcher gate.
- `missing_context_keys` and `invalid_context_keys`: exact context fields to correct.
- `evidence_grade`: always `L2-fixture-or-dry-run` for this endpoint because it is a dry preflight.
- `next_required_action`: the next gate to clear before live read can be attempted.
- `side_effect_boundary`: `dry_preflight_only_no_meta_graph_call_no_production_write`.

This endpoint is a dry preflight only. It does not prove Meta account ownership,
approved permissions, valid token scope, live endpoint reachability, or production
write approval.

## Local Fixture Verification

Run the local fixture/API gates:

```bash
uv --directory apps/api run pytest tests/test_capture_authorizations_api.py tests/test_capture_capabilities_api.py tests/test_instagram_graph_capture.py tests/test_collection_tasks_api.py
pnpm --filter @plugin-hub/web test -- tests/api.test.ts tests/config.test.ts
```

Passing fixture tests proves parser, worker, API contract, and UI parsing behavior only. It is not evidence of authorized Meta live access.

## Authorized Live Read-Only Gate

After credentials and rights are confirmed:

1. Configure `PLUGIN_HUB_INSTAGRAM_GRAPH_ACCESS_TOKEN` only in the backend runtime environment.
2. Configure `PLUGIN_HUB_INSTAGRAM_GRAPH_LIVE_READ_ENABLED=true` only after live-read approval.
3. Start the API and verify `/api/capture-capabilities` reports Graph `task_authorization_required`.
4. Create a collection task with `requested_capture_method=server_instagram_graph_comments` and this context shape:

```json
{
  "media_id": "17900000000000001",
  "authorization_scope": "instagram_graph_live_read",
  "authorized_by": "reviewer-name-or-ticket",
  "authorized_at": "2026-06-21T00:00:00Z",
  "environment": "local",
  "production_write": false
}
```

5. Run the task in a non-production or explicitly approved environment.
6. Confirm task context stores a sanitized `graph_url` with no `access_token`.

## Fail-Closed Cases

- Missing backend token: `credential_missing` at readiness layer and `instagram_graph_access_token_required` at worker layer.
- Token configured but live-read switch closed: `live_read_blocked` at readiness layer and `instagram_graph_live_read_not_enabled` at worker layer.
- Live-read switch enabled but task lacks authorization context: `task_authorization_required` at readiness layer and `instagram_graph_live_read_authorization_required` at worker layer.
- `production_write` is not explicitly `false`: worker blocks before any Graph request.

All fail-closed cases must stop before a Graph request is made.

## Forbidden Until Separately Approved

- Instagram DOM scraping.
- Printing, committing, or returning Meta token values.
- Production VOC writes.
- Broad public feed scraping.
- Treating fixture success as live Meta access success.

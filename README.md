# Plugin Hub

VOC-first Chrome extension and private backend for Amazon and Reddit customer voice collection.

## P0 Scope

- Amazon review capture
- Reddit thread capture
- Private backend ingest
- Schema-based VOC ETL
- VOC Hub review surface

## Planned Local Apps

- `apps/api`: FastAPI backend
- `apps/extension`: Chrome extension
- `apps/web`: Next.js VOC Hub

## Local Development

Run backend:

```bash
cd apps/api
uv run uvicorn plugin_hub_api.main:create_app --factory --reload --port 8000
```

Run VOC Hub:

```bash
pnpm --filter @plugin-hub/web dev
```

Run extension tests:

```bash
pnpm --filter @plugin-hub/extension test
```

Run backend tests:

```bash
cd apps/api
uv run pytest
```

Run full workspace checks:

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm build
```

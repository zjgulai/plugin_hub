# Plugin Hub

VOC-first Chrome extension and private backend for Amazon and Reddit customer voice collection.

## P0 Scope

- Amazon review capture from browser review pages
- Reddit thread capture through the `.json?raw_json=1` entrypoint
- Private backend ingest and persistence
- Schema-based raw-to-canonical VOC ETL
- VOC Hub evidence review surface

## Apps

- `apps/api`: FastAPI backend with Pydantic and SQLAlchemy
- `apps/extension`: Manifest V3 Chrome extension
- `apps/web`: Next.js VOC Hub

## Local Development

Install dependencies:

```bash
pnpm install
uv --directory apps/api sync
```

Run backend:

```bash
cd apps/api
uv run uvicorn plugin_hub_api.main:create_app --factory --reload --port 8000
```

The backend defaults to `sqlite+pysqlite:///./plugin_hub.db` under `apps/api`.
Override it with `PLUGIN_HUB_DATABASE_URL` when needed:

```bash
PLUGIN_HUB_DATABASE_URL=sqlite+pysqlite:///./plugin_hub-dev.db \
  uv run uvicorn plugin_hub_api.main:create_app --factory --reload --port 8000
```

Run VOC Hub:

```bash
PLUGIN_HUB_API_URL=http://localhost:8000 pnpm --filter @plugin-hub/web dev
```

If port `8000` is occupied, run the API on another local port and set the same API URL in VOC Hub and the extension popup.

## Chrome Extension

Build the extension:

```bash
pnpm --filter @plugin-hub/extension build
```

Create a Chrome install package:

```bash
pnpm package:extension
```

The zip package is written to `tmp/outputs/plugin-hub-extension-<version>.zip`.
Use `apps/extension/dist` for local unpacked testing and the zip package for Chrome Web Store upload or manual release handoff.

Load `apps/extension/dist` in Chrome:

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Select Load unpacked.
4. Choose `apps/extension/dist`.

Use the extension:

1. Start the backend.
2. Open an Amazon review page or Reddit thread page.
3. Open the Plugin Hub popup.
4. Confirm the API URL.
5. Click `采集并回传`.

The extension follows Amazon next-page links up to the current page budget and records `stop_reason`. Reddit capture uses the `.json?raw_json=1` thread payload and records `more` node gaps.

## Quality Gates

Run full workspace checks:

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm build
git diff --check
```

Run backend tests only:

```bash
uv --directory apps/api run pytest
```

Run extension tests only:

```bash
pnpm --filter @plugin-hub/extension test
```

## Notes

- P0 covers Amazon and Reddit only.
- The product does not bypass CAPTCHA, login restrictions, platform limits, or anti-abuse controls.
- Low-coverage capture paths must keep explicit `stop_reason`, `coverage_scope`, and `coverage_confidence`.
- Do not commit `.env`, local databases, build outputs, uploaded temporary files, or browser automation artifacts.

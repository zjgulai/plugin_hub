# Plugin Hub

VOC-first Chrome extensions and a shared private backend for Amazon and Reddit customer voice collection.

## P0 Scope

- Amazon review capture from browser review pages
- Reddit thread capture through the `.json?raw_json=1` entrypoint
- Private backend ingest and persistence
- Schema-based raw-to-canonical VOC ETL
- VOC Hub evidence review surface

## Apps

- `apps/api`: FastAPI backend with Pydantic and SQLAlchemy
- `apps/extension`: Manifest V3 Chrome extension source that builds separate Amazon and Reddit packages
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

## Chrome Extensions

Plugin Hub ships one browser plugin per platform while keeping one shared backend and VOC Hub:

- `Plugin Hub Amazon VOC Collector`: Amazon product/review page capture only
- `Plugin Hub Reddit VOC Collector`: Reddit thread capture only
- `Plugin Hub Instagram VOC Collector`: Instagram authorization-gated media/comment evidence only

The plugins share one backend and canonical VOC contracts while keeping platform-specific capture entrypoints and authorization gates separate.

Build all extensions:

```bash
pnpm --filter @plugin-hub/extension build
```

Build one extension:

```bash
pnpm --filter @plugin-hub/extension build:amazon
pnpm --filter @plugin-hub/extension build:reddit
pnpm --filter @plugin-hub/extension build:instagram
```

Create Chrome install packages for all extensions:

```bash
pnpm package:extension
```

Create one package:

```bash
pnpm package:extension:amazon
pnpm package:extension:reddit
pnpm package:extension:instagram
```

The zip packages are written to:

- `tmp/outputs/plugin-hub-amazon-voc-<version>.zip`
- `tmp/outputs/plugin-hub-reddit-voc-<version>.zip`
- `tmp/outputs/plugin-hub-instagram-voc-<version>.zip`

Use the matching directory under `apps/extension/dist/<target>` for local unpacked testing and the zip packages for Chrome Web Store upload or manual release handoff.

### Plugin Versions

Amazon, Reddit, and Instagram versions are managed independently in `apps/extension/extension-versions.json`. The managed format is numeric `MAJOR.MINOR.PATCH`; each segment must be between `0` and `65535` and the version cannot be all zero.

List or validate all plugin versions:

```bash
pnpm version:extension:list
pnpm version:extension:check
```

Preview or apply one plugin bump:

```bash
pnpm run version:extension:bump -- reddit patch --dry-run
pnpm run version:extension:bump -- reddit patch
```

Manifest generation, packaging, and package verification fail when a plugin version is missing, invalid, or different from its built manifest. Before a Chrome Web Store update, also confirm that the candidate version is greater than that plugin's currently published version.

After a version bump, rebuild and verify the affected package before release. The Instagram package exposes an authorization-gated collection path; a successful build does not prove a live Graph capture.

Load an unpacked extension in Chrome:

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Select Load unpacked.
4. Choose the matching `apps/extension/dist/amazon`, `apps/extension/dist/reddit`, or `apps/extension/dist/instagram` directory.

Use the extensions:

1. Start the backend.
2. Open an Amazon product/review page for the Amazon plugin, or a Reddit thread page for the Reddit plugin.
3. Open the matching Plugin Hub popup.
4. Confirm the API URL.
5. Click `采集并回传`.

The Amazon extension follows Amazon next-page links up to the current page budget and records `stop_reason`. The Reddit extension uses the `.json?raw_json=1` thread payload and records `more` node gaps.

## Quality Gates

Run full workspace checks:

```bash
pnpm test
pnpm lint
pnpm typecheck
pnpm build
git diff --check
```

Verify extension packages:

```bash
pnpm verify:extension
pnpm verify:extension:amazon
pnpm verify:extension:reddit
pnpm verify:extension:instagram
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

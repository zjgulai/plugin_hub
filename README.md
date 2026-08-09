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

### API Access Control

Local development defaults to `PLUGIN_HUB_API_AUTH_MODE=disabled`. Production
deployment is configured to fail closed and requires distinct read and write
keys of at least 32 characters:

```bash
PLUGIN_HUB_API_AUTH_MODE=required
PLUGIN_HUB_API_READ_KEY=<independent-read-key>
PLUGIN_HUB_API_WRITE_KEY=<independent-write-key>
```

The API accepts keys through `X-Plugin-Hub-Api-Key`. VOC Hub injects its keys
server-side from environment variables. Browser plugins store the write key in
`chrome.storage.local`; configure it through the extension popup. Never compile
a production key into an extension package or frontend bundle.

Extension API targets are restricted to the configured production origin or an
explicit loopback development origin (`http://localhost[:port]` or
`http://127.0.0.1[:port]`). The page command bar only displays the active
target: it cannot replace it in a runtime message. The service worker validates
the sender and stored target before reading or attaching the API key.

The lightweight health endpoints are:

- `GET /healthz`: process liveness without a database scan.
- `GET /readyz`: database connectivity through `SELECT 1`.

### Data Asset History

The backend persists collection runs, raw source items, and canonical VOC in one
transaction. Operators can inspect aggregate and run-level history without
returning raw payloads:

- `GET /api/data-assets/summary`
- `GET /api/data-assets/runs`
- `GET /api/voc-units?limit=100&offset=0`

Reddit `more` nodes remain preserved in raw/canonical history but are excluded
from analysis-eligible evidence metrics and read-time insight generation.

The read-time insight endpoints remain available, but immutable history is
created only through explicit snapshot writes:

- `POST /api/insights/snapshots`
- `GET /api/insights/snapshots`
- `GET /api/insights/snapshots/{analysis_run_id}`

Each snapshot fixes the collection-run set, input digest, generation/template
contract, Chinese output payloads, per-artifact digest, and aggregate output
digest. Database triggers reject update and delete operations. Repeating the
same platform/language snapshot against unchanged inputs returns the existing
deterministic analysis run instead of duplicating it.

Snapshot tables and the three core evidence tables (`collection_runs`,
`raw_source_items`, and `canonical_voc_units`) are owned by explicit migrations
and are not created by application startup. A fresh local database must run
`up` before routes or workers that use those tables. `status` is read-only and
verifies the recorded checksums plus the core table, index, foreign-key, and
immutability-trigger contracts:

```bash
uv --directory apps/api run python -m plugin_hub_api.migration_cli status
uv --directory apps/api run python -m plugin_hub_api.migration_cli up
```

The core migrations add run-scoped source-identity uniqueness and reject
UPDATE, DELETE, and replacement-style overwrite of raw/canonical evidence.
`down` is permitted only while the tables owned by the latest migration are
empty; populated core evidence fails closed with `core_evidence_rows_exist`.
Never label a new baseline snapshot as historical output from before its
`created_at` time.

Any copied-production rehearsal, backup, production migration, deployment, or
break-glass repair requires separate authorization. The snapshot copy rehearsal
tool is `scripts/dry-run-insight-snapshot-migration.py --copied-database`; the
core-evidence emergency boundary is documented in
`docs/workflows/plugin-hub-core-evidence-break-glass-runbook-draft-20260809.md`.

### Verified SQLite Backups

Create a consistent backup with SQLite's online Backup API:

```bash
uv --directory apps/api run python -m plugin_hub_api.backup_cli \
  --source /path/to/plugin_hub.db \
  --destination-dir /path/to/backups \
  --retention-count 14
```

The command verifies `PRAGMA quick_check`, writes table counts and SHA-256 to a
manifest, atomically publishes the backup, and only counts an older copy toward
retention after rechecking its size, digest, integrity, and table counts.
SQLite database and active WAL/SHM files are restricted to mode `0600` during
application initialization. Production data and backup directories must also
be owned by the service account and set to `0700` during an approved deployment.
The systemd service/timer templates under
`deploy/tencent-lighthouse/systemd/` are deployment artifacts; adding them to
the repository does not mean they are installed in production.

For a second-host encrypted copy, `scripts/pull-offhost-backup.zsh` verifies the
latest remote manifest/database, streams them through SSH directly into an age
encrypted archive, decrypts into a temporary directory for recovery checks,
and retains 30 encrypted archives. The age identity must remain in Keychain;
only its recipient public key belongs in the runtime configuration. The local
LaunchAgent installation is machine-specific and must not be inferred from the
presence of the script in the repository.

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
4. Confirm the trusted API URL and write key in the popup.
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

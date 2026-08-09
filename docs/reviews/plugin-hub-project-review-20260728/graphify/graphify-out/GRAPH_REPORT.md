# Graph Report - docs/reviews/plugin-hub-project-review-20260728/graphify  (2026-07-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1877 nodes · 5145 edges · 92 communities (84 shown, 8 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 509 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7b1c6590`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- etl.py
- test_collection_runs_api.py
- reddit-parser.ts
- api.ts
- services/insights.py
- page.tsx
- routes/insights.py
- upload-client.ts
- isRecord
- verify-extension-package.mjs
- test_collection_tasks_api.py
- reddit_capture.py
- Settings
- ContentCommandBar.tsx
- PlatformWorkspace.tsx
- build_engine
- collection_task_worker.py
- init_database
- VocEvidenceTable.tsx
- Platform
- platform_settings.py
- instagram_capture.py
- service-worker.ts
- amazon-parser.ts
- Popup.tsx
- SqlAlchemyRepository
- page-detect.ts
- extension-target.ts
- repositories.py
- backup_cli.py
- test_contracts.py
- CollectionTask
- scripts
- instagram_graph_capture.py
- SourceKind
- Canvas
- reddit_thread_captures.py
- routes/collection_runs.py
- schemas.py
- ensure_json_object
- capture_authorizations.py
- devDependencies
- devDependencies
- reddit-capture.ts
- amazon-capture.ts
- compilerOptions
- buildPlatformCard
- insight_snapshots.py
- EnrichedVocSignal
- content-script-runtime.tsx
- compilerOptions
- main
- parseInsightBrief
- api-auth.ts
- run_collection_task_endpoint
- test_migration_dry_run_script.py
- export-payload.ts
- config.ts
- worker_cli.py
- extension/package.json
- page-snapshot.ts
- capture_capabilities.py
- data_assets.py
- web/package.json
- scripts
- capture-types.ts
- package.json
- InsightBriefPanel.tsx
- include
- test_capture_authorizations_api.py
- test_capture_capabilities_api.py
- test_platform_settings_api.py
- test_reddit_capture.py
- include
- lib
- scripts
- test_instagram_media_capture_api.py
- test_reddit_thread_capture_api.py
- QualityBadge.tsx
- test_cors.py
- layout.tsx
- test_liveness_and_readiness_do_not_scan_voc_history
- types
- start-collection-worker.sh
- services/__init__.py
- next.config.ts
- next-env.d.ts
- plugin-hub-api
- model_validator

## God Nodes (most connected - your core abstractions)
1. `SqlAlchemyRepository` - 120 edges
2. `Platform` - 66 edges
3. `StrictBaseModel` - 57 edges
4. `Settings` - 43 edges
5. `CollectionTaskWorkerConfig` - 39 edges
6. `CollectionTaskClaimLostError` - 37 edges
7. `RawSourceItem` - 36 edges
8. `ensure_json_object()` - 33 edges
9. `get_repository()` - 29 edges
10. `isRecord()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `Settings`  [EXTRACTED]
  scripts/dry-run-insight-snapshot-migration.py → apps/api/src/plugin_hub_api/config.py
- `main()` --calls--> `create_app()`  [EXTRACTED]
  scripts/dry-run-insight-snapshot-migration.py → apps/api/src/plugin_hub_api/main.py
- `main()` --calls--> `apply_pending_migrations()`  [EXTRACTED]
  scripts/dry-run-insight-snapshot-migration.py → apps/api/src/plugin_hub_api/migrations.py
- `main()` --calls--> `applied_migration_versions()`  [EXTRACTED]
  scripts/dry-run-insight-snapshot-migration.py → apps/api/src/plugin_hub_api/migrations.py
- `main()` --calls--> `rollback_latest_migration()`  [EXTRACTED]
  scripts/dry-run-insight-snapshot-migration.py → apps/api/src/plugin_hub_api/migrations.py

## Import Cycles
- None detected.

## Communities (92 total, 8 thin omitted)

### Community 0 - "etl.py"
Cohesion: 0.07
Nodes (78): `ensure_json_value()`, `map_raw_item_to_voc()`, `_optional_reddit_thread_fullname()`, `CanonicalVocUnit`, `CollectionRun`, `JsonValue`, `RawSourceItem`, `_raise_reddit_comment_thread_id_required()` (+70 more)

### Community 1 - "test_collection_runs_api.py"
Cohesion: 0.07
Nodes (70): `extension_payload_hash_matches()`, `fnv1a64_payload_hash()`, `_javascript_number_string()`, `JsonValue`, `_stable_stringify()`, `model_validator`, `generate_strategy_notes()`, `_amazon_review_item()` (+62 more)

### Community 2 - "reddit-parser.ts"
Cohesion: 0.07
Nodes (59): `ParseAmazonReviewsResult`, `absoluteUrl()`, `attribute()`, `attributeFromFirst()`, `buildCommentRawSourceItem()`, `buildDomCommentData()`, `buildDomCommentRawSourceItems()`, `buildDomThreadData()` (+51 more)

### Community 3 - "api.ts"
Cohesion: 0.06
Nodes (62): `fetchPlatformSettingAuditEventsForActivePlatforms()`, `loadDashboardData()`, `ActionRecommendation`, `BriefConfidence`, `buildCaptureCapabilitiesUrl()`, `buildCollectionTasksUrl()`, `buildDataAssetRunsUrl()`, `buildDataAssetSummaryUrl()` (+54 more)

### Community 4 - "services/insights.py"
Cohesion: 0.09
Nodes (55): `ActionRecommendation`, `_action()`, `_action_for_signal()`, `_action_plan()`, `_append_signal_example()`, `_brief_confidence()`, `_brief_confidence_level()`, `_brief_confidence_reason()` (+47 more)

### Community 5 - "page.tsx"
Cohesion: 0.06
Nodes (44): `AuthorizationPanel()`, `capabilityStatusLabel()`, `capabilityTone()`, `CollectionTaskPanel()`, `commaListFormValue()`, `ConfigPanel()`, `contextNumber()`, `contextString()` (+36 more)

### Community 6 - "routes/insights.py"
Cohesion: 0.13
Nodes (42): `AnalysisSnapshotSchemaNotReady`, `_artifact_from_row()`, `_artifact_parameters()`, `InsightSnapshotRepository`, `_json()`, `_json_list()`, `_json_object()`, `JsonValue` (+34 more)

### Community 7 - "upload-client.ts"
Cohesion: 0.10
Nodes (44): `apiHeaders()`, `assertCollectionRunPayloadJson()`, `assertCollectionTaskPayloadJson()`, `buildCollectionIdempotencyKey()`, `createCollectionTask()`, `getInsightBriefs()`, `getPlatformSetting()`, `getStrategyNotes()` (+36 more)

### Community 8 - "isRecord"
Cohesion: 0.12
Nodes (45): `isJsonValue()`, `isRecord()`, `jsonList()`, `jsonObject()`, `optionalBoolean()`, `optionalNumber()`, `optionalPagination()`, `optionalSnapshotMaxId()` (+37 more)

### Community 9 - "verify-extension-package.mjs"
Cohesion: 0.08
Nodes (37): `bumpManagedExtensionVersion()`, `compareManagedExtensionVersions()`, `formatManagedExtensionVersion()`, `isRecord()`, `loadExtensionVersionState()`, `parseManagedExtensionVersion()`, `readJson()`, `RELEASE_TYPES` (+29 more)

### Community 10 - "test_collection_tasks_api.py"
Cohesion: 0.11
Nodes (43): `_access_denied_fetcher()`, `_blocked_instagram_graph_fetcher()`, `_empty_payload_fetcher()`, `_enable_instagram_graph_live_read()`, `_fixture_fetcher()`, `_instagram_graph_fetcher()`, `_nested_reddit_payload_fetcher()`, `datetime` (+35 more)

### Community 11 - "reddit_capture.py"
Cohesion: 0.12
Nodes (41): `Any`, `_build_comment_raw_source_item()`, `_build_more_raw_source_item()`, `_build_raw_source_item()`, `build_reddit_json_url()`, `_build_selected_payload()`, `_build_thread_raw_source_item()`, `capture_reddit_thread_json()` (+33 more)

### Community 12 - "Settings"
Cohesion: 0.10
Nodes (35): `API_KEY_HEADER`, `SecretStr`, `_secret_value()`, `Settings`, `create_app()`, `_matches()`, `Request`, `SecretStr` (+27 more)

### Community 13 - "ContentCommandBar.tsx"
Cohesion: 0.10
Nodes (33): `buildPipelineSteps()`, `captureSummaryStatusText()`, `CommandBarStatus`, `detectedObjectSubtitle()`, `detectedObjectTitle()`, `formatConfidencePercent()`, `PipelineStep`, `platformName()` (+25 more)

### Community 14 - "PlatformWorkspace.tsx"
Cohesion: 0.07
Nodes (28): `PlatformSettingSubmitButton()`, `ACTIVE_PLATFORMS`, `ActivePlatformDefinition`, `AuditChangeList()`, `auditFieldLabel()`, `auditValue()`, `booleanConfig()`, `contextString()` (+20 more)

### Community 15 - "build_engine"
Cohesion: 0.16
Nodes (31): `build_engine()`, `main()`, `_print_status()`, `_read_migration_status()`, `_applied_migration_checksums()`, `applied_migration_versions()`, `apply_pending_migrations()`, `_begin_sqlite_ddl_transaction()` (+23 more)

### Community 16 - "collection_task_worker.py"
Cohesion: 0.19
Nodes (32): `build_collection_task_capture_handlers()`, `_capture_instagram_fixture_task()`, `_capture_instagram_graph_comments_task()`, `_capture_reddit_task()`, `_collection_task_claim_token()`, `_configured_instagram_graph_fetcher()`, `_context_bool()`, `_context_int()` (+24 more)

### Community 17 - "init_database"
Cohesion: 0.15
Nodes (29): `_configure_sqlite_connections()`, `init_database()`, `make_session_factory()`, `Engine`, `Session`, `_restrict_sqlite_file_permissions()`, `Path`, `test_data_asset_summary_uses_one_snapshot_during_concurrent_insert()` (+21 more)

### Community 18 - "VocEvidenceTable.tsx"
Cohesion: 0.10
Nodes (28): `activeFilterChips()`, `ContextSummary()`, `dateMs()`, `extensionString()`, `filterUnits()`, `formatDate()`, `formatPlatform()`, `PlatformFilter` (+20 more)

### Community 19 - "Platform"
Cohesion: 0.27
Nodes (35): `CollectionTaskClaimLostError`, `RuntimeError`, `Raised when a worker tries to write with an expired or replaced lease.`, `CollectionTaskRequest`, `CollectionTaskResponse`, `CollectionTaskRunResponse`, `CollectionTasksResponse`, `create_collection_task()` (+27 more)

### Community 20 - "platform_settings.py"
Cohesion: 0.19
Nodes (31): `get_repository()`, `Session`, `_boolean()`, `_changed_fields()`, `_default_config()`, `_default_setting()`, `get_platform_setting()`, `_graph_api_version()` (+23 more)

### Community 21 - "instagram_capture.py"
Cohesion: 0.13
Nodes (27): `create_instagram_media_comment_capture()`, `InstagramMediaCommentsCaptureRequest`, `InstagramMediaCommentsCaptureResponse`, `Depends`, `field_validator`, `JsonValue`, `model_validator`, `post` (+19 more)

### Community 22 - "service-worker.ts"
Cohesion: 0.13
Nodes (27): `CreateCollectionTaskResponse`, `GetInsightBriefsResponse`, `GetPlatformSettingResponse`, `GetStrategyNotesResponse`, `isCollectionRunPayloadLike()`, `isCollectionTaskPayloadLike()`, `isCreateCollectionTaskMessage()`, `isGetInsightBriefsMessage()` (+19 more)

### Community 23 - "amazon-parser.ts"
Cohesion: 0.16
Nodes (27): `buildRawSourceItem()`, `cleanAmazonReviewBodyText()`, `collectReviewContainers()`, `isRatingText()`, `normalizeNullable()`, `parseAmazonReviews()`, `ParseAmazonReviewsInput`, `parseCapturedAt()` (+19 more)

### Community 24 - "Popup.tsx"
Cohesion: 0.15
Nodes (22): `assertHttpUrl()`, `clearPendingCollectionUpload()`, `isPendingCollectionUpload()`, `isRecord()`, `loadApiBaseUrl()`, `loadApiKey()`, `loadPendingCollectionUpload()`, `normalizeApiBaseUrl()` (+14 more)

### Community 25 - "SqlAlchemyRepository"
Cohesion: 0.13
Nodes (11): `PlatformSettingRow`, `_platform_setting_row()`, `CollectionTaskStatus`, `DataAssetSummary`, `Platform`, `PlatformSetting`, `Session`, `SqlAlchemyRepository` (+3 more)

### Community 26 - "page-detect.ts"
Cohesion: 0.16
Nodes (22): `captureCurrentPage()`, `normalizeRuntimeExtensionTarget()`, `targetSupportsPlatform()`, `AMAZON_ALLOWED_HOSTNAMES`, `AmazonReviewsPage`, `buildAmazonReviewsPage()`, `detectAmazonPage()`, `detectInstagramMediaPage()` (+14 more)

### Community 27 - "extension-target.ts"
Cohesion: 0.15
Nodes (19): `buildIconSet()`, `buildManifest()`, `manifest`, `CURRENT_EXTENSION_TARGET`, `EXTENSION_TARGET_SET`, `ExtensionTarget`, `ExtensionTargetConfig`, `ExtensionTargetRegistry` (+11 more)

### Community 28 - "repositories.py"
Cohesion: 0.18
Nodes (18): `Base`, `CanonicalVocUnitRow`, `CollectionRunRow`, `PlatformSettingAuditEventRow`, `RawSourceItemRow`, `_canonical_voc_unit_row()`, `_collection_run_row()`, `_datetime_signature()` (+10 more)

### Community 29 - "backup_cli.py"
Cohesion: 0.23
Nodes (21): `BackupResult`, `BackupVerification`, `create_verified_backup()`, `main()`, `_manifest_matches_backup()`, `_prune_verified_backups()`, `datetime`, `Path` (+13 more)

### Community 30 - "test_contracts.py"
Cohesion: 0.10
Nodes (10): `Plugin Hub API package.`, `parametrize`, `test_canonical_voc_unit_rejects_non_strict_confidence()`, `test_collection_run_create_accepts_confidence_boundaries()`, `test_collection_run_create_rejects_confidence_outside_boundaries()`, `test_collection_run_create_rejects_non_strict_confidence()`, `test_raw_source_item_keeps_platform_schema_version()`, `test_raw_source_item_rejects_non_json_payload_shapes()` (+2 more)

### Community 31 - "CollectionTask"
Cohesion: 0.22
Nodes (12): `CollectionTaskRow`, `_claimed_collection_task()`, `_collection_task_is_claimable()`, `_collection_task_is_runnable()`, `_collection_task_row()`, `_is_running_task_stale()`, `_parse_iso_datetime()`, `CollectionTask` (+4 more)

### Community 32 - "scripts"
Cohesion: 0.09
Nodes (23): `scripts`, `build`, `collection:worker`, `collection:worker:daemon`, `collection:worker:once`, `lint`, `lint:api`, `package:extension` (+15 more)

### Community 33 - "instagram_graph_capture.py"
Cohesion: 0.15
Nodes (19): `build_instagram_graph_media_comments_url()`, `capture_instagram_media_comments_graph()`, `_coerce_fetch_result()`, `_graph_error_code()`, `InstagramGraphConfig`, `InstagramGraphFetchResult`, `InstagramGraphMediaCommentsCaptureResult`, `_parse_graph_response_body()` (+11 more)

### Community 34 - "SourceKind"
Cohesion: 0.22
Nodes (10): `SourceKind`, `build_reddit_oauth_api_url()`, `_parse_oauth_token_response()`, `RedditAccessToken`, `RedditOAuthConfig`, `RedditOAuthJsonFetcher`, `RedditRedirectHandler`, `test_reddit_oauth_fetcher_gets_token_and_fetches_from_oauth_api()` (+2 more)

### Community 35 - "Canvas"
Cohesion: 0.26
Nodes (11): `Color`, `Canvas`, `clamp()`, `draw_amazon()`, `draw_instagram()`, `draw_reddit()`, `main()`, `mix()` (+3 more)

### Community 36 - "reddit_thread_captures.py"
Cohesion: 0.21
Nodes (12): `create_reddit_thread_capture()`, `_effective_stop_reason()`, `Depends`, `Exception`, `model_validator`, `post`, `_reddit_capture_error_detail()`, `RedditThreadCaptureRequest` (+4 more)

### Community 37 - "routes/collection_runs.py"
Cohesion: 0.21
Nodes (17): `alias`, `CollectionReplayState`, `_collection_run_id()`, `CollectionRunRequest`, `CollectionRunResponse`, `create_collection_run()`, `list_voc_units()`, `Depends` (+9 more)

### Community 38 - "schemas.py"
Cohesion: 0.35
Nodes (16): `ActionRecommendation`, `BriefConfidence`, `BusinessSignal`, `DataGap`, `EvidenceReference`, `ExecutiveFinding`, `InsightScope`, `PlatformSettingAuditEventsResponse` (+8 more)

### Community 39 - "ensure_json_object"
Cohesion: 0.27
Nodes (4): `ensure_json_object()`, `datetime`, `field_validator`, `JsonValue`

### Community 40 - "capture_authorizations.py"
Cohesion: 0.19
Nodes (13): `InstagramGraphLiveReadPreflightRequest`, `InstagramGraphLiveReadPreflightResponse`, `_next_required_action()`, `preflight_instagram_graph_live_read_authorization()`, `_preflight_status()`, `field_validator`, `JsonValue`, `post` (+5 more)

### Community 41 - "devDependencies"
Cohesion: 0.12
Nodes (16): `devDependencies`, `esbuild`, `jsdom`, `@types/chrome`, `@types/react`, `vite`, `@vitejs/plugin-react`, `vitest` (+8 more)

### Community 42 - "devDependencies"
Cohesion: 0.12
Nodes (16): `eslint`, `@types/react-dom`, `typescript-eslint`, `devDependencies`, `eslint`, `@next/eslint-plugin-next`, `@types/node`, `@types/react-dom` (+8 more)

### Community 43 - "reddit-capture.ts"
Cohesion: 0.18
Nodes (9): `buildRedditJsonUrl()`, `captureRedditThread()`, `captureRedditThreadDomFallback()`, `errorMessage()`, `parseCapturedAt()`, `redditCoverageConfidence()`, `redditDomFallbackCoverageConfidence()`, `resolveDocumentRoot()` (+1 more)

### Community 44 - "amazon-capture.ts"
Cohesion: 0.25
Nodes (12): `amazonCoverageConfidence()`, `AmazonPageEvidence`, `captureAmazonCurrentPage()`, `captureAmazonReviews()`, `inferMarketplace()`, `normalizeAmazonPageLimit()`, `observedAmazonPage()`, `parseCapturedAt()` (+4 more)

### Community 45 - "compilerOptions"
Cohesion: 0.13
Nodes (15): `compilerOptions`, `allowJs`, `allowSyntheticDefaultImports`, `esModuleInterop`, `forceConsistentCasingInFileNames`, `isolatedModules`, `jsx`, `module` (+7 more)

### Community 46 - "buildPlatformCard"
Cohesion: 0.15
Nodes (15): `buildPlatformCard()`, `capabilityNoteFor()`, `capabilityStatusLabel()`, `capabilityToneFor()`, `countOpenTasks()`, `extensionString()`, `freshnessLabel()`, `latestDate()` (+7 more)

### Community 47 - "insight_snapshots.py"
Cohesion: 0.35
Nodes (13): `AnalysisArtifactType`, `_artifact_snapshot()`, `build_insight_snapshot()`, `_canonical_json()`, `_digest_json()`, `InsightSnapshotBuild`, `CanonicalVocUnit`, `datetime` (+5 more)

### Community 48 - "EnrichedVocSignal"
Cohesion: 0.25
Nodes (14): `EnrichedVocSignal`, `_business_aspect()`, `_business_impact()`, `_business_signal_type()`, `_business_signals()`, `_business_topic()`, `_customer_language()`, `_dedupe_business_signals()` (+6 more)

### Community 49 - "content-script-runtime.tsx"
Cohesion: 0.21
Nodes (8): `ContentScriptOptions`, `isCaptureCurrentPageMessage()`, `isRecord()`, `mountContentScript()`, `MountedCommandBar`, `DetectedPage`, `CaptureCurrentPageResponse`, `CaptureCurrentPageSuccess`

### Community 50 - "compilerOptions"
Cohesion: 0.14
Nodes (14): `compilerOptions`, `allowJs`, `esModuleInterop`, `incremental`, `isolatedModules`, `jsx`, `module`, `moduleResolution` (+6 more)

### Community 51 - "main"
Cohesion: 0.31
Nodes (13): `_artifact_replace_guard_enforced()`, `_insert_guard_trigger_names()`, `_integrity()`, `main()`, `Connection`, `Engine`, `Path`, `refuse_live_database_path()` (+5 more)

### Community 52 - "parseInsightBrief"
Cohesion: 0.35
Nodes (13): `isPlatform()`, `nullableNumber()`, `parseActionRecommendation()`, `parseBriefConfidence()`, `parseBusinessSignal()`, `parseDataGap()`, `parseEvidenceReference()`, `parseExecutiveFinding()` (+5 more)

### Community 53 - "api-auth.ts"
Cohesion: 0.24
Nodes (10): `captureRedditThreadAction()`, `platformFromForm()`, `stableError()`, `updatePlatformSettingAction()`, `ApiFetcher`, `ApiAccessKeys`, `apiFetcherWithKey()`, `EnvSource` (+2 more)

### Community 54 - "run_collection_task_endpoint"
Cohesion: 0.29
Nodes (12): `get_collection_task_worker_config()`, `get_instagram_graph_comments_fetcher()`, `get_reddit_json_fetcher()`, `list_collection_tasks()`, `Depends`, `get`, `InstagramGraphCommentsFetcher`, `Platform` (+4 more)

### Community 55 - "test_migration_dry_run_script.py"
Cohesion: 0.30
Nodes (10): `_load_script()`, `CaptureFixture`, `MonkeyPatch`, `parametrize`, `Path`, `test_dry_run_allows_database_copy_outside_live_roots()`, `test_dry_run_refuses_host_and_container_live_database_roots()`, `test_dry_run_rejects_missing_insert_guard_with_applied_migration_row()` (+2 more)

### Community 56 - "export-payload.ts"
Cohesion: 0.29
Nodes (9): `buildExportFilename()`, `buildPayloadJson()`, `buildRawItemsCsv()`, `downloadTextFile()`, `escapeCsvCell()`, `sourceIdFromPayload()`, `stringValue()`, `textField()` (+1 more)

### Community 57 - "config.ts"
Cohesion: 0.27
Nodes (9): `VocPlatform`, `boundedNumber()`, `DashboardConfig`, `DEFAULT_ENABLED_PLATFORMS`, `EnvSource`, `loadDashboardConfig()`, `platformList()`, `positiveInteger()` (+1 more)

### Community 58 - "worker_cli.py"
Cohesion: 0.31
Nodes (9): `build_config()`, `build_worker_engine()`, `main()`, `parse_args()`, `Engine`, `InstagramGraphCommentsFetcher`, `Session`, `run_worker()` (+1 more)

### Community 59 - "extension/package.json"
Cohesion: 0.20
Nodes (9): `dependencies`, `react`, `react-dom`, `react`, `name`, `private`, `type`, `react-dom` (+1 more)

### Community 60 - "page-snapshot.ts"
Cohesion: 0.42
Nodes (9): `attributeFromSelector()`, `extractAmazonRating()`, `extractAmazonReviewCount()`, `getPageSnapshot()`, `marketplaceFromUrl()`, `normalizeRatingText()`, `PageSnapshot`, `subredditFromUrl()` (+1 more)

### Community 61 - "capture_capabilities.py"
Cohesion: 0.33
Nodes (8): `CaptureCapabilitiesResponse`, `CaptureCapability`, `_instagram_graph_next_required_action()`, `_instagram_graph_status()`, `list_capture_capabilities()`, `get`, `Request`, `CaptureStatus`

### Community 62 - "data_assets.py"
Cohesion: 0.36
Nodes (8): `DataAssetRunsResponse`, `get_data_asset_summary()`, `list_data_asset_runs()`, `DataAssetSummary`, `Depends`, `get`, `DataAssetRun`, `DataAssetSummary`

### Community 63 - "web/package.json"
Cohesion: 0.22
Nodes (8): `dependencies`, `next`, `react`, `react`, `name`, `private`, `type`, `next`

### Community 64 - "scripts"
Cohesion: 0.25
Nodes (8): `scripts`, `build`, `build:amazon`, `build:instagram`, `build:reddit`, `lint`, `test`, `typecheck`

### Community 65 - "capture-types.ts"
Cohesion: 0.32
Nodes (6): `CaptureCurrentPageInput`, `CaptureRuntimeSettings`, `amazonRuntimeSettingsFromPlatformSetting()`, `configInteger()`, `loadCaptureRuntimeSettings()`, `CaptureCurrentPageMessage`

### Community 66 - "package.json"
Cohesion: 0.25
Nodes (7): `typescript`, `devDependencies`, `typescript`, `typescript`, `name`, `packageManager`, `private`

### Community 67 - "InsightBriefPanel.tsx"
Cohesion: 0.36
Nodes (5): `InsightBriefPanel()`, `InsightBriefPanelProps`, `priorityScore()`, `selectPrimaryBrief()`, `InsightBrief`

### Community 68 - "include"
Cohesion: 0.25
Nodes (7): `exclude`, `include`, `next-env.d.ts`, `.next/types/**/*.ts`, `node_modules`, `**/*.ts`, `**/*.tsx`

### Community 69 - "test_capture_authorizations_api.py"
Cohesion: 0.48
Nodes (6): `TestClient`, `test_instagram_graph_live_read_preflight_rejects_non_object_context()`, `test_instagram_graph_live_read_preflight_reports_context_gaps()`, `test_instagram_graph_live_read_preflight_reports_live_read_blocked()`, `test_instagram_graph_live_read_preflight_reports_missing_credential()`, `test_instagram_graph_live_read_preflight_reports_ready()`

### Community 70 - "test_capture_capabilities_api.py"
Cohesion: 0.62
Nodes (6): `_capability()`, `TestClient`, `test_capture_capabilities_includes_existing_platform_methods()`, `test_capture_capabilities_reports_instagram_graph_authorization_gate()`, `test_capture_capabilities_reports_live_read_blocked_when_only_fetcher_exists()`, `test_capture_capabilities_reports_task_authorization_gate_when_live_read_is_enabled()`

### Community 71 - "test_platform_settings_api.py"
Cohesion: 0.48
Nodes (6): `TestClient`, `_setting()`, `test_platform_setting_patch_persists_and_records_audit()`, `test_platform_setting_patch_rejects_sensitive_config_keys()`, `test_platform_setting_patch_rejects_unknown_and_out_of_range_config()`, `test_platform_settings_returns_defaults_without_sensitive_values()`

### Community 72 - "test_reddit_capture.py"
Cohesion: 0.29
Nodes (6): `parametrize`, `test_build_reddit_json_url_adds_raw_json_without_losing_query()`, `test_build_reddit_json_url_rejects_non_reddit_network_targets()`, `test_build_reddit_oauth_api_url_moves_reddit_json_path_to_oauth_host()`, `test_parse_reddit_thread_json_payload_returns_thread_and_comment_raw_items()`, `test_reddit_redirect_handler_rejects_redirect_before_private_target_fetch()`

### Community 73 - "include"
Cohesion: 0.29
Nodes (6): `include`, `eslint.config.js`, `manifest.config.ts`, `src`, `tests`, `vite.config.ts`

### Community 74 - "lib"
Cohesion: 0.29
Nodes (7): `lib`, `DOM`, `lib`, `dom`, `dom.iterable`, `ES2022`, `esnext`

### Community 75 - "scripts"
Cohesion: 0.29
Nodes (7): `scripts`, `build`, `dev`, `lint`, `start`, `test`, `typecheck`

### Community 76 - "test_instagram_media_capture_api.py"
Cohesion: 0.60
Nodes (4): `TestClient`, `test_post_instagram_media_comment_capture_persists_voc_units()`, `test_post_instagram_media_comment_capture_rejects_empty_fixture()`, `test_post_instagram_media_comment_capture_rejects_non_instagram_source()`

### Community 77 - "test_reddit_thread_capture_api.py"
Cohesion: 0.60
Nodes (4): `TestClient`, `test_post_reddit_thread_capture_fetches_json_and_persists_voc_units()`, `test_post_reddit_thread_capture_maps_network_errors_to_stable_response()`, `test_post_reddit_thread_capture_rejects_private_network_target_before_fetch()`

### Community 78 - "QualityBadge.tsx"
Cohesion: 0.40
Nodes (4): `QualityBadge()`, `QualityBadgeProps`, `reviewLabels`, `ReviewState`

### Community 79 - "test_cors.py"
Cohesion: 0.67
Nodes (3): `TestClient`, `test_chrome_extension_origin_can_preflight_collection_run_upload()`, `test_reddit_page_origin_cannot_preflight_collection_run_upload()`

### Community 82 - "types"
Cohesion: 0.67
Nodes (3): `types`, `chrome`, `vitest/globals`

## Knowledge Gaps
- **217 isolated node(s):** `plugin-hub-api`, `manifest`, `name`, `private`, `type` (+212 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SqlAlchemyRepository` connect `SqlAlchemyRepository` to `test_collection_runs_api.py`, `reddit_thread_captures.py`, `routes/collection_runs.py`, `routes/insights.py`, `test_collection_tasks_api.py`, `collection_task_worker.py`, `init_database`, `Platform`, `platform_settings.py`, `instagram_capture.py`, `run_collection_task_endpoint`, `worker_cli.py`, `repositories.py`, `data_assets.py`, `CollectionTask`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Platform` connect `Platform` to `etl.py`, `SourceKind`, `reddit_thread_captures.py`, `routes/collection_runs.py`, `routes/insights.py`, `schemas.py`, `capture_authorizations.py`, `services/insights.py`, `reddit_capture.py`, `insight_snapshots.py`, `collection_task_worker.py`, `platform_settings.py`, `instagram_capture.py`, `SqlAlchemyRepository`, `repositories.py`, `capture_capabilities.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `ensure_json_object()` connect `ensure_json_object` to `etl.py`, `instagram_graph_capture.py`, `schemas.py`, `routes/insights.py`, `capture_authorizations.py`, `reddit_capture.py`, `insight_snapshots.py`, `collection_task_worker.py`, `instagram_capture.py`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `SqlAlchemyRepository` (e.g. with `CanonicalVocUnitRow` and `CollectionRunRow`) actually correct?**
  _`SqlAlchemyRepository` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `Platform` (e.g. with `AnalysisSnapshotSchemaNotReady` and `InsightSnapshotRepository`) actually correct?**
  _`Platform` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `StrictBaseModel` (e.g. with `InstagramGraphLiveReadPreflightRequest` and `InstagramGraphLiveReadPreflightResponse`) actually correct?**
  _`StrictBaseModel` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Settings` (e.g. with `InstagramGraphAccessError` and `InstagramGraphCommentsFetcherClient`) actually correct?**
  _`Settings` has 15 INFERRED edges - model-reasoned connections that need verification._
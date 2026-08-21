export type JsonScalar = string | number | boolean | null;
export type JsonValue = JsonScalar | JsonValue[] | { [key: string]: JsonValue };

export type VocPlatform = "amazon" | "reddit" | "instagram";
export type VocPlatformFilter = VocPlatform | "all";

export type VocUnit = {
  source_object_id: string;
  platform: VocPlatform;
  source_kind: string;
  title: string | null;
  body: string;
  quality_flags: string[];
  coverage_confidence: number;
  platform_extension: Record<string, JsonValue>;
  source_url: string;
  captured_at: string;
  created_at: string | null;
  asin: string | null;
  marketplace: string | null;
  thread_id: string | null;
  parent_id: string | null;
  depth: number | null;
  reply_role: string | null;
  collection_run_id: string | null;
  author_display: string | null;
  commercial_object_type: string | null;
  brand: string | null;
  product_title: string | null;
};

export type VocUnitsResponse = {
  items: VocUnit[];
  total?: number;
  limit?: number;
  offset?: number;
  snapshot_max_id?: number | null;
};

export type CollectionTaskStatus =
  | "pending"
  | "running"
  | "retry_scheduled"
  | "completed"
  | "failed";

export type CollectionTask = {
  collection_task_id: string;
  platform: VocPlatform;
  source_url: string;
  requested_capture_method: string;
  trigger_reason: string;
  status: CollectionTaskStatus;
  context: Record<string, JsonValue>;
  created_at: string;
  updated_at: string;
};

export type CollectionTasksResponse = {
  items: CollectionTask[];
  open_total: number;
  open_totals: Record<VocPlatform, number>;
  total?: number;
  limit?: number;
  offset?: number;
};

export type DataAssetSummary = {
  collection_run_count: number;
  raw_item_count: number;
  canonical_voc_count: number;
  analysis_eligible_voc_count: number;
  placeholder_voc_count: number;
  flagged_voc_count: number;
  low_confidence_voc_count: number;
  average_coverage_confidence: number;
  runs_with_count_mismatch: number;
  orphan_raw_count: number;
  orphan_voc_count: number;
  platform_counts: Record<VocPlatform, number>;
  latest_run_at: string | null;
  latest_capture_at: string | null;
};

export type DataAssetRun = {
  collection_run_id: string;
  platform: VocPlatform;
  capture_method: string;
  stop_reason: string | null;
  coverage_confidence: number;
  created_at: string;
  first_captured_at: string | null;
  last_captured_at: string | null;
  raw_item_count: number;
  canonical_voc_count: number;
  analysis_eligible_voc_count: number;
  placeholder_voc_count: number;
  asset_state: "complete" | "empty" | "mismatch";
};

export type DataAssetRunsResponse = {
  items: DataAssetRun[];
  total: number;
  limit: number;
  offset: number;
};

export type AnalysisArtifactType =
  | "relation_edge"
  | "enriched_voc_signal"
  | "strategy_note"
  | "insight_brief";

export type AnalysisRunSnapshot = {
  analysis_run_id: string;
  platform: VocPlatform;
  language: string;
  scope: Record<string, JsonValue>;
  collection_run_ids: string[];
  input_digest: string;
  template_contract: Record<string, JsonValue>;
  snapshot_schema_version: string;
  generation_method: string;
  source_unit_count: number;
  analysis_unit_count: number;
  truncated: boolean;
  artifact_count: number;
  output_digest: string;
  created_at: string;
};

export type AnalysisArtifactSnapshot = {
  analysis_snapshot_id: string;
  analysis_run_id: string;
  artifact_type: AnalysisArtifactType;
  artifact_key: string;
  schema_version: string;
  payload: Record<string, JsonValue>;
  payload_digest: string;
  created_at: string;
};

export type AnalysisSnapshotsResponse = {
  items: AnalysisRunSnapshot[];
  total: number;
  limit: number;
  offset: number;
};

export type AnalysisSnapshotDetail = {
  run: AnalysisRunSnapshot;
  artifacts: AnalysisArtifactSnapshot[];
};

export type CaptureCapabilityMode = "extension" | "server" | "fixture";
export type CaptureCapabilityStatus =
  | "ready"
  | "authorization_required"
  | "fixture_only"
  | "credential_missing"
  | "live_read_blocked"
  | "task_authorization_required";

export type CaptureCapability = {
  platform: VocPlatform;
  capture_method: string;
  mode: CaptureCapabilityMode;
  status: CaptureCapabilityStatus;
  configured: boolean;
  requires_authorization: boolean;
  live_read_enabled: boolean;
  live_write_enabled: boolean;
  writes_canonical_voc: boolean;
  required_context_keys: string[];
  evidence_grade: string;
  next_required_action: string;
  side_effect_boundary: string;
  notes: string;
};

export type CaptureCapabilitiesResponse = {
  items: CaptureCapability[];
};

export type PlatformSettingSource = "default" | "stored";

export type PlatformSetting = {
  platform: VocPlatform;
  enabled: boolean;
  config: Record<string, JsonValue>;
  updated_at: string;
  updated_by: string;
  source: PlatformSettingSource;
};

export type PlatformSettingsResponse = {
  items: PlatformSetting[];
};

export type PlatformSettingUpdate = {
  enabled?: boolean;
  config?: Record<string, JsonValue>;
  updated_by?: string;
};

export type PlatformSettingAuditEvent = {
  id: number;
  platform: VocPlatform;
  changed_fields: string[];
  previous_enabled: boolean | null;
  new_enabled: boolean | null;
  previous_config: Record<string, JsonValue>;
  new_config: Record<string, JsonValue>;
  changed_by: string;
  created_at: string;
};

export type PlatformSettingAuditEventsResponse = {
  items: PlatformSettingAuditEvent[];
};

export type InstagramGraphLiveReadPreflightStatus =
  | "ready"
  | "credential_missing"
  | "live_read_blocked"
  | "task_authorization_required";

export type InstagramGraphLiveReadPreflightResponse = {
  platform: "instagram";
  capture_method: "server_instagram_graph_comments";
  status: InstagramGraphLiveReadPreflightStatus;
  configured: boolean;
  live_read_enabled: boolean;
  task_authorization_ready: boolean;
  ready_for_worker: boolean;
  required_context_keys: string[];
  missing_context_keys: string[];
  invalid_context_keys: string[];
  blocking_code: string | null;
  evidence_grade: string;
  next_required_action: string;
  side_effect_boundary: string;
  notes: string;
};

export type StrategyNote = {
  strategy_type: string;
  topic: string;
  evidence_count: number;
  evidence_examples: JsonValue[];
  recommendation: string;
  evidence_strength: number;
  quality_flags: string[];
};

export type StrategyNotesResponse = {
  items: StrategyNote[];
};

export type InsightScope = {
  platform: VocPlatform;
  source_object_type: string;
  source_object_id: string;
  source_url: string;
  collection_run_ids: string[];
  coverage_scope: string;
  coverage_confidence: number;
};

export type ExecutiveFinding = {
  finding_id: string;
  title: string;
  business_meaning: string;
  priority: string;
  confidence_level: string;
  evidence_ref_ids: string[];
};

export type BusinessSignal = {
  signal_id: string;
  signal_type: string;
  topic: string;
  aspect: string;
  customer_language: string[];
  business_impact: string;
  severity: string;
  priority: string;
  evidence_strength: string;
  confidence_reason: string;
  evidence_ref_ids: string[];
  quality_flags: string[];
};

export type ActionRecommendation = {
  action_id: string;
  action_type: string;
  title: string;
  recommendation: string;
  why_now: string;
  expected_metric: string;
  owner_role: string;
  priority: string;
  effort: string;
  evidence_ref_ids: string[];
};

export type EvidenceReference = {
  evidence_ref_id: string;
  voc_unit_id: string;
  platform: VocPlatform;
  source_kind: string;
  source_object_id: string;
  quote: string;
  normalized_quote: string | null;
  rating: number | null;
  relation_edge_ids: string[];
  quality_flags: string[];
  source_url: string;
};

export type BriefConfidence = {
  level: string;
  reason: string;
  evidence_count: number;
  source_diversity: string;
  coverage_notes: string[];
};

export type DataGap = {
  gap_type: string;
  description: string;
  recommended_collection: string;
  blocks_confidence: boolean;
};

export type InsightBrief = {
  brief_id: string;
  template_id: string;
  template_version: string;
  language: string;
  advisor_profile: string;
  scope: InsightScope;
  headline: string;
  executive_findings: ExecutiveFinding[];
  business_signals: BusinessSignal[];
  action_plan: ActionRecommendation[];
  evidence_refs: EvidenceReference[];
  confidence: BriefConfidence;
  data_gaps: DataGap[];
  generation_method: string;
  created_at: string;
};

export type InsightBriefsResponse = {
  items: InsightBrief[];
};

export type RedditThreadCaptureResponse = {
  collection_run_id: string;
  raw_item_count: number;
  voc_unit_count: number;
  json_url: string;
  more_node_count: number;
  stop_reason: string | null;
  coverage_confidence: number;
};

type FetchResponse = {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
};

export type ApiFetcher = (url: string, init?: RequestInit) => Promise<FetchResponse>;
export type VocUnitsFetcher = ApiFetcher;
export type VocUnitsFetchOptions = {
  maxItems?: number;
};

export async function fetchVocUnits(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  fetcher: VocUnitsFetcher = async (url) => fetch(url),
  options: VocUnitsFetchOptions = {}
): Promise<VocUnitsResponse> {
  const maxItems = options.maxItems;
  if (maxItems !== undefined && (!Number.isSafeInteger(maxItems) || maxItems < 1)) {
    throw new Error("voc_units_invalid_options:max_items_positive_integer_required");
  }
  const pageSize = Math.min(maxItems ?? 500, 500);
  const firstPage = await fetchVocUnitsPage(apiBaseUrl, platform, pageSize, 0, fetcher);
  const total = firstPage.total;
  if (total === undefined) {
    return maxItems === undefined
      ? firstPage
      : { ...firstPage, items: firstPage.items.slice(0, maxItems) };
  }
  const targetItemCount = Math.min(total, maxItems ?? total);
  if (firstPage.items.length >= targetItemCount) {
    return { ...firstPage, items: firstPage.items.slice(0, targetItemCount) };
  }
  const snapshotMaxId = firstPage.snapshot_max_id;
  if (snapshotMaxId === undefined || snapshotMaxId === null) {
    throw new Error("voc_units_invalid_response:snapshot_boundary_required");
  }

  const items = [...firstPage.items];
  const itemKeys = new Set(items.map(vocUnitIdentity));
  let offset = (firstPage.offset ?? 0) + firstPage.items.length;
  while (items.length < targetItemCount) {
    const page = await fetchVocUnitsPage(
      apiBaseUrl,
      platform,
      pageSize,
      offset,
      fetcher,
      snapshotMaxId
    );
    if (page.snapshot_max_id !== snapshotMaxId) {
      throw new Error("voc_units_invalid_response:snapshot_boundary_changed");
    }
    if (page.items.length === 0) {
      throw new Error("voc_units_invalid_response:pagination_stalled");
    }
    for (const item of page.items) {
      const itemKey = vocUnitIdentity(item);
      if (!itemKeys.has(itemKey) && items.length < targetItemCount) {
        itemKeys.add(itemKey);
        items.push(item);
      }
    }
    offset += page.items.length;
  }

  return {
    items,
    total,
    limit: pageSize,
    offset: 0,
    snapshot_max_id: snapshotMaxId
  };
}

function vocUnitIdentity(unit: VocUnit): string {
  return [
    unit.platform,
    unit.source_kind,
    unit.collection_run_id ?? `${unit.captured_at}\u0000${unit.source_url}`,
    unit.source_object_id
  ].join("\u0000");
}

async function fetchVocUnitsPage(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  limit: number,
  offset: number,
  fetcher: VocUnitsFetcher,
  snapshotMaxId?: number
): Promise<VocUnitsResponse> {
  const response = await fetcher(
    buildVocUnitsUrl(apiBaseUrl, platform, limit, offset, snapshotMaxId)
  );
  if (!response.ok) {
    throw new Error(`voc_units_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response);
  return parseVocUnitsResponse(payload);
}

export async function fetchDataAssetSummary(
  apiBaseUrl: string,
  lowConfidenceThreshold: number,
  fetcher: ApiFetcher = async (url) => fetch(url)
): Promise<DataAssetSummary> {
  const response = await fetcher(
    buildDataAssetSummaryUrl(apiBaseUrl, lowConfidenceThreshold)
  );
  if (!response.ok) {
    throw new Error(`data_asset_summary_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "data_asset_summary_invalid_response");
  return parseDataAssetSummary(payload);
}

export async function fetchDataAssetRuns(
  apiBaseUrl: string,
  fetcher: ApiFetcher = async (url) => fetch(url)
): Promise<DataAssetRunsResponse> {
  const response = await fetcher(buildDataAssetRunsUrl(apiBaseUrl));
  if (!response.ok) {
    throw new Error(`data_asset_runs_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "data_asset_runs_invalid_response");
  return parseDataAssetRunsResponse(payload);
}

export async function fetchAnalysisSnapshots(
  apiBaseUrl: string,
  fetcher: ApiFetcher = async (url) => fetch(url)
): Promise<AnalysisSnapshotsResponse> {
  const response = await fetcher(buildAnalysisSnapshotsUrl(apiBaseUrl));
  if (!response.ok) {
    throw new Error(`analysis_snapshots_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "analysis_snapshots_invalid_response");
  return parseAnalysisSnapshotsResponse(payload);
}

export async function fetchAnalysisSnapshotDetail(
  apiBaseUrl: string,
  analysisRunId: string,
  fetcher: ApiFetcher = async (url) => fetch(url)
): Promise<AnalysisSnapshotDetail> {
  const response = await fetcher(buildAnalysisSnapshotDetailUrl(apiBaseUrl, analysisRunId));
  if (!response.ok) {
    throw new Error(`analysis_snapshot_detail_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "analysis_snapshot_detail_invalid_response");
  const detail = parseAnalysisSnapshotDetail(payload);
  if (detail.run.analysis_run_id !== analysisRunId) {
    throw new Error("analysis_snapshot_detail_invalid_response:selected_run_mismatch");
  }
  return detail;
}

export async function fetchStrategyNotes(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<StrategyNotesResponse> {
  const response = await fetcher(buildStrategyNotesUrl(apiBaseUrl, platform));
  if (!response.ok) {
    throw new Error(`strategy_notes_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response);
  return {
    items: parseStrategyNotesResponse(payload)
  };
}

export async function fetchInsightBriefs(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<InsightBriefsResponse> {
  const response = await fetcher(buildInsightBriefsUrl(apiBaseUrl, platform));
  if (!response.ok) {
    throw new Error(`insight_briefs_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "insight_briefs_invalid_response");
  return {
    items: parseInsightBriefsResponse(payload)
  };
}

export async function fetchCollectionTasks(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<CollectionTasksResponse> {
  const response = await fetcher(buildCollectionTasksUrl(apiBaseUrl, platform));
  if (!response.ok) {
    throw new Error(`collection_tasks_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "collection_tasks_invalid_response");
  return parseCollectionTasksResponse(payload);
}

export async function fetchCaptureCapabilities(
  apiBaseUrl: string,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<CaptureCapabilitiesResponse> {
  const response = await fetcher(buildCaptureCapabilitiesUrl(apiBaseUrl));
  if (!response.ok) {
    throw new Error(`capture_capabilities_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "capture_capabilities_invalid_response");
  return {
    items: parseCaptureCapabilitiesResponse(payload)
  };
}

export async function fetchPlatformSettings(
  apiBaseUrl: string,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<PlatformSettingsResponse> {
  const response = await fetcher(buildPlatformSettingsUrl(apiBaseUrl));
  if (!response.ok) {
    throw new Error(`platform_settings_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(response, "platform_settings_invalid_response");
  return {
    items: parsePlatformSettingsResponse(payload)
  };
}

export async function updatePlatformSetting(
  apiBaseUrl: string,
  platform: VocPlatform,
  update: PlatformSettingUpdate,
  fetcher: ApiFetcher = async (url, init) => fetch(url, init)
): Promise<PlatformSetting> {
  const response = await fetcher(buildPlatformSettingUrl(apiBaseUrl, platform), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(update)
  });
  if (!response.ok) {
    const detail = await responseErrorDetail(response);
    throw new Error(
      [
        `platform_setting_update_failed:${response.status}`,
        detail
      ].filter(Boolean).join(":")
    );
  }

  const payload = await parseJson(response, "platform_setting_invalid_response");
  return parsePlatformSetting(payload, "platform_setting_invalid_response");
}

export async function fetchPlatformSettingAuditEvents(
  apiBaseUrl: string,
  platform: VocPlatform,
  fetcher: VocUnitsFetcher = async (url) => fetch(url)
): Promise<PlatformSettingAuditEventsResponse> {
  const response = await fetcher(buildPlatformSettingAuditEventsUrl(apiBaseUrl, platform));
  if (!response.ok) {
    throw new Error(`platform_setting_audit_events_fetch_failed:${response.status}`);
  }

  const payload = await parseJson(
    response,
    "platform_setting_audit_events_invalid_response"
  );
  return {
    items: parsePlatformSettingAuditEventsResponse(payload)
  };
}

export async function preflightInstagramGraphLiveReadAuthorization(
  apiBaseUrl: string,
  context: Record<string, JsonValue>,
  fetcher: ApiFetcher = async (url, init) => fetch(url, init)
): Promise<InstagramGraphLiveReadPreflightResponse> {
  const response = await fetcher(buildInstagramGraphLiveReadPreflightUrl(apiBaseUrl), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      context
    })
  });
  if (!response.ok) {
    throw new Error(`instagram_graph_live_read_preflight_failed:${response.status}`);
  }

  const payload = await parseJson(
    response,
    "instagram_graph_live_read_preflight_invalid_response"
  );
  return parseInstagramGraphLiveReadPreflightResponse(payload);
}

export async function captureRedditThreadByUrl(
  apiBaseUrl: string,
  sourceUrl: string,
  fetcher: ApiFetcher = async (url, init) => fetch(url, init)
): Promise<RedditThreadCaptureResponse> {
  const response = await fetcher(buildRedditThreadCapturesUrl(apiBaseUrl), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      source_url: sourceUrl
    })
  });
  if (!response.ok) {
    throw new Error(`reddit_thread_capture_failed:${response.status}`);
  }

  const payload = await parseJson(response, "reddit_thread_capture_invalid_response");
  return parseRedditThreadCaptureResponse(payload);
}

function buildVocUnitsUrl(
  apiBaseUrl: string,
  platform: VocPlatformFilter,
  limit: number,
  offset: number,
  snapshotMaxId?: number
): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  const endpoint = `${normalizedBaseUrl}/api/voc-units`;
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  if (platform !== "all") {
    params.set("platform", platform);
  }
  if (snapshotMaxId !== undefined) {
    params.set("snapshot_max_id", String(snapshotMaxId));
  }
  return `${endpoint}?${params.toString()}`;
}

function buildDataAssetSummaryUrl(
  apiBaseUrl: string,
  lowConfidenceThreshold: number
): string {
  const endpoint = `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/data-assets/summary`;
  const params = new URLSearchParams({
    low_confidence_threshold: String(lowConfidenceThreshold)
  });
  return `${endpoint}?${params.toString()}`;
}

function buildDataAssetRunsUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/data-assets/runs?limit=50&offset=0`;
}

function buildAnalysisSnapshotsUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/insights/snapshots?limit=50&offset=0`;
}

function buildAnalysisSnapshotDetailUrl(
  apiBaseUrl: string,
  analysisRunId: string
): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  return `${normalizedBaseUrl}/api/insights/snapshots/${encodeURIComponent(analysisRunId)}`;
}

function buildCollectionTasksUrl(apiBaseUrl: string, platform: VocPlatformFilter): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  const endpoint = `${normalizedBaseUrl}/api/collection-tasks`;
  if (platform === "all") {
    return endpoint;
  }

  return `${endpoint}?platform=${platform}`;
}

function buildRedditThreadCapturesUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/reddit-thread-captures`;
}

function buildCaptureCapabilitiesUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/capture-capabilities`;
}

function buildPlatformSettingsUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/platform-settings`;
}

function buildPlatformSettingUrl(apiBaseUrl: string, platform: VocPlatform): string {
  return `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/platform-settings/${platform}`;
}

function buildPlatformSettingAuditEventsUrl(
  apiBaseUrl: string,
  platform: VocPlatform
): string {
  return `${buildPlatformSettingUrl(apiBaseUrl, platform)}/audit-events`;
}

function buildInstagramGraphLiveReadPreflightUrl(apiBaseUrl: string): string {
  return `${apiBaseUrl.trim().replace(/\/+$/, "")}/api/capture-authorizations/instagram-graph-live-read/preflight`;
}

function buildStrategyNotesUrl(apiBaseUrl: string, platform: VocPlatformFilter): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  const endpoint = `${normalizedBaseUrl}/api/insights/strategy-notes`;
  if (platform === "all") {
    return endpoint;
  }

  return `${endpoint}?platform=${platform}`;
}

function buildInsightBriefsUrl(apiBaseUrl: string, platform: VocPlatformFilter): string {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "");
  const endpoint = `${normalizedBaseUrl}/api/insights/briefs`;
  if (platform === "all") {
    return endpoint;
  }

  return `${endpoint}?platform=${platform}`;
}

async function parseJson(
  response: FetchResponse,
  errorPrefix = "voc_units_invalid_response"
): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    throw new Error(`${errorPrefix}:json_parse_failed`, {
      cause: error
    });
  }
}

async function responseErrorDetail(response: FetchResponse): Promise<string | null> {
  try {
    const payload = await response.json();
    if (!isRecord(payload)) {
      return null;
    }
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return payload.detail;
    }
    return null;
  } catch {
    return null;
  }
}

function parseVocUnitsResponse(payload: unknown): VocUnitsResponse {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("voc_units_invalid_response:items_array_required");
  }

  return {
    items: payload.items.map(parseVocUnit),
    ...optionalPagination(payload),
    snapshot_max_id: optionalSnapshotMaxId(payload.snapshot_max_id)
  };
}

function optionalSnapshotMaxId(value: unknown): number | null | undefined {
  if (value === null) {
    return null;
  }
  if (value === undefined) {
    return undefined;
  }
  if (!Number.isSafeInteger(value) || Number(value) < 0) {
    throw new Error("voc_units_invalid_response:snapshot_max_id_required");
  }
  return Number(value);
}

function parseCollectionTasksResponse(payload: unknown): CollectionTasksResponse {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("collection_tasks_invalid_response:items_array_required");
  }

  return {
    items: payload.items.map(parseCollectionTask),
    open_total: requiredFiniteIntegerFor(
      payload.open_total,
      "open_total",
      "collection_tasks_invalid_response"
    ),
    open_totals: parsePlatformCounts(
      payload.open_totals,
      "collection_tasks_invalid_response",
      "open_totals"
    ),
    ...optionalPagination(payload)
  };
}

function parsePlatformCounts(
  value: unknown,
  errorPrefix: string,
  fieldPrefix: string
): Record<VocPlatform, number> {
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:${fieldPrefix}_object_required`);
  }
  return {
    amazon: requiredFiniteIntegerFor(value.amazon, `${fieldPrefix}.amazon`, errorPrefix),
    reddit: requiredFiniteIntegerFor(value.reddit, `${fieldPrefix}.reddit`, errorPrefix),
    instagram: requiredFiniteIntegerFor(value.instagram, `${fieldPrefix}.instagram`, errorPrefix)
  };
}

function parseDataAssetSummary(payload: unknown): DataAssetSummary {
  if (!isRecord(payload) || !isRecord(payload.platform_counts)) {
    throw new Error("data_asset_summary_invalid_response:object_required");
  }

  return {
    collection_run_count: requiredFiniteIntegerFor(
      payload.collection_run_count,
      "collection_run_count",
      "data_asset_summary_invalid_response"
    ),
    raw_item_count: requiredFiniteIntegerFor(
      payload.raw_item_count,
      "raw_item_count",
      "data_asset_summary_invalid_response"
    ),
    canonical_voc_count: requiredFiniteIntegerFor(
      payload.canonical_voc_count,
      "canonical_voc_count",
      "data_asset_summary_invalid_response"
    ),
    analysis_eligible_voc_count: requiredFiniteIntegerFor(
      payload.analysis_eligible_voc_count,
      "analysis_eligible_voc_count",
      "data_asset_summary_invalid_response"
    ),
    placeholder_voc_count: requiredFiniteIntegerFor(
      payload.placeholder_voc_count,
      "placeholder_voc_count",
      "data_asset_summary_invalid_response"
    ),
    flagged_voc_count: requiredFiniteIntegerFor(
      payload.flagged_voc_count,
      "flagged_voc_count",
      "data_asset_summary_invalid_response"
    ),
    low_confidence_voc_count: requiredFiniteIntegerFor(
      payload.low_confidence_voc_count,
      "low_confidence_voc_count",
      "data_asset_summary_invalid_response"
    ),
    average_coverage_confidence: requiredFiniteNumber(
      payload.average_coverage_confidence,
      "average_coverage_confidence",
      "data_asset_summary_invalid_response"
    ),
    runs_with_count_mismatch: requiredFiniteIntegerFor(
      payload.runs_with_count_mismatch,
      "runs_with_count_mismatch",
      "data_asset_summary_invalid_response"
    ),
    orphan_raw_count: requiredFiniteIntegerFor(
      payload.orphan_raw_count,
      "orphan_raw_count",
      "data_asset_summary_invalid_response"
    ),
    orphan_voc_count: requiredFiniteIntegerFor(
      payload.orphan_voc_count,
      "orphan_voc_count",
      "data_asset_summary_invalid_response"
    ),
    platform_counts: {
      amazon: requiredFiniteIntegerFor(
        payload.platform_counts.amazon,
        "platform_counts.amazon",
        "data_asset_summary_invalid_response"
      ),
      reddit: requiredFiniteIntegerFor(
        payload.platform_counts.reddit,
        "platform_counts.reddit",
        "data_asset_summary_invalid_response"
      ),
      instagram: requiredFiniteIntegerFor(
        payload.platform_counts.instagram,
        "platform_counts.instagram",
        "data_asset_summary_invalid_response"
      )
    },
    latest_run_at: optionalString(payload.latest_run_at),
    latest_capture_at: optionalString(payload.latest_capture_at)
  };
}

function parseDataAssetRunsResponse(payload: unknown): DataAssetRunsResponse {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("data_asset_runs_invalid_response:items_array_required");
  }
  const pagination = optionalPagination(payload);
  if (
    pagination.total === undefined ||
    pagination.limit === undefined ||
    pagination.offset === undefined
  ) {
    throw new Error("data_asset_runs_invalid_response:pagination_required");
  }
  return {
    items: payload.items.map(parseDataAssetRun),
    total: pagination.total,
    limit: pagination.limit,
    offset: pagination.offset
  };
}

function parseDataAssetRun(value: unknown): DataAssetRun {
  if (!isRecord(value)) {
    throw new Error("data_asset_runs_invalid_response:item_object_required");
  }
  const assetState = value.asset_state;
  if (assetState !== "complete" && assetState !== "empty" && assetState !== "mismatch") {
    throw new Error("data_asset_runs_invalid_response:asset_state_required");
  }
  return {
    collection_run_id: requiredStringFor(
      value.collection_run_id,
      "collection_run_id",
      "data_asset_runs_invalid_response"
    ),
    platform: requiredPlatform(value.platform, "data_asset_runs_invalid_response"),
    capture_method: requiredStringFor(
      value.capture_method,
      "capture_method",
      "data_asset_runs_invalid_response"
    ),
    stop_reason: optionalString(value.stop_reason),
    coverage_confidence: requiredFiniteNumber(
      value.coverage_confidence,
      "coverage_confidence",
      "data_asset_runs_invalid_response"
    ),
    created_at: requiredStringFor(
      value.created_at,
      "created_at",
      "data_asset_runs_invalid_response"
    ),
    first_captured_at: optionalString(value.first_captured_at),
    last_captured_at: optionalString(value.last_captured_at),
    raw_item_count: requiredFiniteIntegerFor(
      value.raw_item_count,
      "raw_item_count",
      "data_asset_runs_invalid_response"
    ),
    canonical_voc_count: requiredFiniteIntegerFor(
      value.canonical_voc_count,
      "canonical_voc_count",
      "data_asset_runs_invalid_response"
    ),
    analysis_eligible_voc_count: requiredFiniteIntegerFor(
      value.analysis_eligible_voc_count,
      "analysis_eligible_voc_count",
      "data_asset_runs_invalid_response"
    ),
    placeholder_voc_count: requiredFiniteIntegerFor(
      value.placeholder_voc_count,
      "placeholder_voc_count",
      "data_asset_runs_invalid_response"
    ),
    asset_state: assetState
  };
}

function parseAnalysisSnapshotsResponse(payload: unknown): AnalysisSnapshotsResponse {
  const errorPrefix = "analysis_snapshots_invalid_response";
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error(`${errorPrefix}:items_array_required`);
  }
  const pagination = optionalPagination(payload);
  if (
    pagination.total === undefined ||
    pagination.limit === undefined ||
    pagination.offset === undefined
  ) {
    throw new Error(`${errorPrefix}:pagination_required`);
  }
  return {
    items: payload.items.map((item) => parseAnalysisRunSnapshot(item, errorPrefix)),
    total: pagination.total,
    limit: pagination.limit,
    offset: pagination.offset
  };
}

function parseAnalysisSnapshotDetail(payload: unknown): AnalysisSnapshotDetail {
  const errorPrefix = "analysis_snapshot_detail_invalid_response";
  if (!isRecord(payload) || !Array.isArray(payload.artifacts)) {
    throw new Error(`${errorPrefix}:object_required`);
  }
  const run = parseAnalysisRunSnapshot(payload.run, errorPrefix);
  const artifacts = payload.artifacts.map((artifact) =>
    parseAnalysisArtifactSnapshot(artifact, errorPrefix)
  );
  if (artifacts.some((artifact) => artifact.analysis_run_id !== run.analysis_run_id)) {
    throw new Error(`${errorPrefix}:artifact_run_mismatch`);
  }
  if (artifacts.length !== run.artifact_count) {
    throw new Error(`${errorPrefix}:artifact_count_mismatch`);
  }
  if (new Set(artifacts.map((artifact) => artifact.analysis_snapshot_id)).size !== artifacts.length) {
    throw new Error(`${errorPrefix}:duplicate_artifact_identity`);
  }
  return { run, artifacts };
}

function parseAnalysisRunSnapshot(
  value: unknown,
  errorPrefix: string
): AnalysisRunSnapshot {
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:run_object_required`);
  }
  return {
    analysis_run_id: requiredStringFor(value.analysis_run_id, "analysis_run_id", errorPrefix),
    platform: requiredPlatform(value.platform, errorPrefix),
    language: requiredStringFor(value.language, "language", errorPrefix),
    scope: requiredJsonObjectFor(value.scope, "scope", errorPrefix),
    collection_run_ids: requiredStringListFor(
      value.collection_run_ids,
      "collection_run_ids",
      errorPrefix
    ),
    input_digest: requiredStringFor(value.input_digest, "input_digest", errorPrefix),
    template_contract: requiredJsonObjectFor(
      value.template_contract,
      "template_contract",
      errorPrefix
    ),
    snapshot_schema_version: requiredStringFor(
      value.snapshot_schema_version,
      "snapshot_schema_version",
      errorPrefix
    ),
    generation_method: requiredStringFor(
      value.generation_method,
      "generation_method",
      errorPrefix
    ),
    source_unit_count: requiredNonNegativeIntegerFor(
      value.source_unit_count,
      "source_unit_count",
      errorPrefix
    ),
    analysis_unit_count: requiredNonNegativeIntegerFor(
      value.analysis_unit_count,
      "analysis_unit_count",
      errorPrefix
    ),
    truncated: requiredBooleanFor(value.truncated, "truncated", errorPrefix),
    artifact_count: requiredNonNegativeIntegerFor(
      value.artifact_count,
      "artifact_count",
      errorPrefix
    ),
    output_digest: requiredStringFor(value.output_digest, "output_digest", errorPrefix),
    created_at: requiredStringFor(value.created_at, "created_at", errorPrefix)
  };
}

function parseAnalysisArtifactSnapshot(
  value: unknown,
  errorPrefix: string
): AnalysisArtifactSnapshot {
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:artifact_object_required`);
  }
  return {
    analysis_snapshot_id: requiredStringFor(
      value.analysis_snapshot_id,
      "analysis_snapshot_id",
      errorPrefix
    ),
    analysis_run_id: requiredStringFor(value.analysis_run_id, "analysis_run_id", errorPrefix),
    artifact_type: requiredAnalysisArtifactType(value.artifact_type, errorPrefix),
    artifact_key: requiredStringFor(value.artifact_key, "artifact_key", errorPrefix),
    schema_version: requiredStringFor(value.schema_version, "schema_version", errorPrefix),
    payload: requiredJsonObjectFor(value.payload, "payload", errorPrefix),
    payload_digest: requiredStringFor(value.payload_digest, "payload_digest", errorPrefix),
    created_at: requiredStringFor(value.created_at, "created_at", errorPrefix)
  };
}

function optionalPagination(
  payload: Record<string, unknown>
): Partial<Pick<VocUnitsResponse, "total" | "limit" | "offset">> {
  const values = [payload.total, payload.limit, payload.offset];
  if (!values.every((value) => Number.isSafeInteger(value) && Number(value) >= 0)) {
    return {};
  }
  return {
    total: Number(payload.total),
    limit: Number(payload.limit),
    offset: Number(payload.offset)
  };
}

function parseCaptureCapabilitiesResponse(payload: unknown): CaptureCapability[] {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("capture_capabilities_invalid_response:items_array_required");
  }

  return payload.items.map(parseCaptureCapability);
}

function parsePlatformSettingsResponse(payload: unknown): PlatformSetting[] {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("platform_settings_invalid_response:items_array_required");
  }

  return payload.items.map((item) => parsePlatformSetting(item, "platform_settings_invalid_response"));
}

function parsePlatformSettingAuditEventsResponse(
  payload: unknown
): PlatformSettingAuditEvent[] {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("platform_setting_audit_events_invalid_response:items_array_required");
  }

  return payload.items.map(parsePlatformSettingAuditEvent);
}

function parseInstagramGraphLiveReadPreflightResponse(
  payload: unknown
): InstagramGraphLiveReadPreflightResponse {
  if (!isRecord(payload)) {
    throw new Error("instagram_graph_live_read_preflight_invalid_response:object_required");
  }

  const platform = requiredPlatform(
    payload.platform,
    "instagram_graph_live_read_preflight_invalid_response"
  );
  if (platform !== "instagram") {
    throw new Error("instagram_graph_live_read_preflight_invalid_response:item_platform_required");
  }
  const captureMethod = requiredStringFor(
    payload.capture_method,
    "capture_method",
    "instagram_graph_live_read_preflight_invalid_response"
  );
  if (captureMethod !== "server_instagram_graph_comments") {
    throw new Error(
      "instagram_graph_live_read_preflight_invalid_response:capture_method_required"
    );
  }

  return {
    platform,
    capture_method: captureMethod,
    status: requiredInstagramGraphLiveReadPreflightStatus(payload.status),
    configured: requiredBooleanFor(
      payload.configured,
      "configured",
      "instagram_graph_live_read_preflight_invalid_response"
    ),
    live_read_enabled: requiredBooleanFor(
      payload.live_read_enabled,
      "live_read_enabled",
      "instagram_graph_live_read_preflight_invalid_response"
    ),
    task_authorization_ready: requiredBooleanFor(
      payload.task_authorization_ready,
      "task_authorization_ready",
      "instagram_graph_live_read_preflight_invalid_response"
    ),
    ready_for_worker: requiredBooleanFor(
      payload.ready_for_worker,
      "ready_for_worker",
      "instagram_graph_live_read_preflight_invalid_response"
    ),
    required_context_keys: stringList(payload.required_context_keys),
    missing_context_keys: stringList(payload.missing_context_keys),
    invalid_context_keys: stringList(payload.invalid_context_keys),
    blocking_code: optionalString(payload.blocking_code),
    evidence_grade: requiredStringFor(
      payload.evidence_grade,
      "evidence_grade",
      "instagram_graph_live_read_preflight_invalid_response"
    ),
    next_required_action: requiredStringFor(
      payload.next_required_action,
      "next_required_action",
      "instagram_graph_live_read_preflight_invalid_response"
    ),
    side_effect_boundary: requiredStringFor(
      payload.side_effect_boundary,
      "side_effect_boundary",
      "instagram_graph_live_read_preflight_invalid_response"
    ),
    notes: requiredStringFor(
      payload.notes,
      "notes",
      "instagram_graph_live_read_preflight_invalid_response"
    )
  };
}

function parseRedditThreadCaptureResponse(payload: unknown): RedditThreadCaptureResponse {
  if (!isRecord(payload)) {
    throw new Error("reddit_thread_capture_invalid_response:object_required");
  }

  return {
    collection_run_id: requiredStringFor(
      payload.collection_run_id,
      "collection_run_id",
      "reddit_thread_capture_invalid_response"
    ),
    raw_item_count: requiredFiniteIntegerFor(
      payload.raw_item_count,
      "raw_item_count",
      "reddit_thread_capture_invalid_response"
    ),
    voc_unit_count: requiredFiniteIntegerFor(
      payload.voc_unit_count,
      "voc_unit_count",
      "reddit_thread_capture_invalid_response"
    ),
    json_url: requiredStringFor(
      payload.json_url,
      "json_url",
      "reddit_thread_capture_invalid_response"
    ),
    more_node_count: requiredFiniteIntegerFor(
      payload.more_node_count,
      "more_node_count",
      "reddit_thread_capture_invalid_response"
    ),
    stop_reason: optionalString(payload.stop_reason),
    coverage_confidence: requiredFiniteNumber(
      payload.coverage_confidence,
      "coverage_confidence",
      "reddit_thread_capture_invalid_response"
    )
  };
}

function parseStrategyNotesResponse(payload: unknown): StrategyNote[] {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("strategy_notes_invalid_response:items_array_required");
  }

  return payload.items.map(parseStrategyNote);
}

function parseInsightBriefsResponse(payload: unknown): InsightBrief[] {
  if (!isRecord(payload) || !Array.isArray(payload.items)) {
    throw new Error("insight_briefs_invalid_response:items_array_required");
  }

  return payload.items.map(parseInsightBrief);
}

function parseCollectionTask(value: unknown): CollectionTask {
  if (!isRecord(value)) {
    throw new Error("collection_tasks_invalid_response:item_object_required");
  }

  return {
    collection_task_id: requiredStringFor(
      value.collection_task_id,
      "collection_task_id",
      "collection_tasks_invalid_response"
    ),
    platform: requiredPlatform(value.platform, "collection_tasks_invalid_response"),
    source_url: requiredStringFor(value.source_url, "source_url", "collection_tasks_invalid_response"),
    requested_capture_method: requiredStringFor(
      value.requested_capture_method,
      "requested_capture_method",
      "collection_tasks_invalid_response"
    ),
    trigger_reason: requiredStringFor(
      value.trigger_reason,
      "trigger_reason",
      "collection_tasks_invalid_response"
    ),
    status: requiredCollectionTaskStatus(value.status),
    context: jsonObject(value.context),
    created_at: requiredStringFor(value.created_at, "created_at", "collection_tasks_invalid_response"),
    updated_at: requiredStringFor(value.updated_at, "updated_at", "collection_tasks_invalid_response")
  };
}

function parseCaptureCapability(value: unknown): CaptureCapability {
  if (!isRecord(value)) {
    throw new Error("capture_capabilities_invalid_response:item_object_required");
  }

  return {
    platform: requiredPlatform(value.platform, "capture_capabilities_invalid_response"),
    capture_method: requiredStringFor(
      value.capture_method,
      "capture_method",
      "capture_capabilities_invalid_response"
    ),
    mode: requiredCaptureCapabilityMode(value.mode),
    status: requiredCaptureCapabilityStatus(value.status),
    configured: requiredBooleanFor(
      value.configured,
      "configured",
      "capture_capabilities_invalid_response"
    ),
    requires_authorization: requiredBooleanFor(
      value.requires_authorization,
      "requires_authorization",
      "capture_capabilities_invalid_response"
    ),
    live_read_enabled: requiredBooleanFor(
      value.live_read_enabled,
      "live_read_enabled",
      "capture_capabilities_invalid_response"
    ),
    live_write_enabled: requiredBooleanFor(
      value.live_write_enabled,
      "live_write_enabled",
      "capture_capabilities_invalid_response"
    ),
    writes_canonical_voc: requiredBooleanFor(
      value.writes_canonical_voc,
      "writes_canonical_voc",
      "capture_capabilities_invalid_response"
    ),
    required_context_keys: stringList(value.required_context_keys),
    evidence_grade: requiredStringFor(
      value.evidence_grade,
      "evidence_grade",
      "capture_capabilities_invalid_response"
    ),
    next_required_action: requiredStringFor(
      value.next_required_action,
      "next_required_action",
      "capture_capabilities_invalid_response"
    ),
    side_effect_boundary: requiredStringFor(
      value.side_effect_boundary,
      "side_effect_boundary",
      "capture_capabilities_invalid_response"
    ),
    notes: requiredStringFor(value.notes, "notes", "capture_capabilities_invalid_response")
  };
}

function parsePlatformSetting(value: unknown, errorPrefix: string): PlatformSetting {
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:item_object_required`);
  }

  return {
    platform: requiredPlatform(value.platform, errorPrefix),
    enabled: requiredBooleanFor(value.enabled, "enabled", errorPrefix),
    config: jsonObject(value.config),
    updated_at: requiredStringFor(value.updated_at, "updated_at", errorPrefix),
    updated_by: requiredStringFor(value.updated_by, "updated_by", errorPrefix),
    source: requiredPlatformSettingSource(value.source, errorPrefix)
  };
}

function parsePlatformSettingAuditEvent(value: unknown): PlatformSettingAuditEvent {
  const errorPrefix = "platform_setting_audit_events_invalid_response";
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:item_object_required`);
  }

  return {
    id: requiredFiniteIntegerFor(value.id, "id", errorPrefix),
    platform: requiredPlatform(value.platform, errorPrefix),
    changed_fields: stringList(value.changed_fields),
    previous_enabled: optionalBoolean(value.previous_enabled),
    new_enabled: optionalBoolean(value.new_enabled),
    previous_config: jsonObject(value.previous_config),
    new_config: jsonObject(value.new_config),
    changed_by: requiredStringFor(value.changed_by, "changed_by", errorPrefix),
    created_at: requiredStringFor(value.created_at, "created_at", errorPrefix)
  };
}

function parseVocUnit(value: unknown): VocUnit {
  if (!isRecord(value)) {
    throw new Error("voc_units_invalid_response:item_object_required");
  }

  return {
    source_object_id: requiredString(value.source_object_id, "source_object_id"),
    platform: requiredPlatform(value.platform),
    source_kind: requiredString(value.source_kind, "source_kind"),
    title: optionalString(value.title),
    body: requiredString(value.body, "body"),
    quality_flags: stringList(value.quality_flags),
    coverage_confidence: requiredFiniteNumber(value.coverage_confidence, "coverage_confidence"),
    platform_extension: jsonObject(value.platform_extension),
    source_url: requiredString(value.source_url, "source_url"),
    captured_at: requiredString(value.captured_at, "captured_at"),
    created_at: optionalString(value.created_at),
    asin: optionalString(value.asin),
    marketplace: optionalString(value.marketplace),
    thread_id: optionalString(value.thread_id),
    parent_id: optionalString(value.parent_id),
    depth: optionalNumber(value.depth),
    reply_role: optionalString(value.reply_role),
    collection_run_id: optionalString(value.collection_run_id),
    author_display: optionalString(value.author_display),
    commercial_object_type: optionalString(value.commercial_object_type),
    brand: optionalString(value.brand),
    product_title: optionalString(value.product_title)
  };
}

function parseStrategyNote(value: unknown): StrategyNote {
  if (!isRecord(value)) {
    throw new Error("strategy_notes_invalid_response:item_object_required");
  }

  return {
    strategy_type: requiredString(value.strategy_type, "strategy_type"),
    topic: requiredString(value.topic, "topic"),
    evidence_count: requiredFiniteInteger(value.evidence_count, "evidence_count"),
    evidence_examples: jsonList(value.evidence_examples),
    recommendation: requiredString(value.recommendation, "recommendation"),
    evidence_strength: requiredFiniteNumber(
      value.evidence_strength,
      "evidence_strength",
      "strategy_notes_invalid_response"
    ),
    quality_flags: stringList(value.quality_flags)
  };
}

function parseInsightBrief(value: unknown): InsightBrief {
  const errorPrefix = "insight_briefs_invalid_response";
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:item_object_required`);
  }

  return {
    brief_id: requiredStringFor(value.brief_id, "brief_id", errorPrefix),
    template_id: requiredStringFor(value.template_id, "template_id", errorPrefix),
    template_version: requiredStringFor(value.template_version, "template_version", errorPrefix),
    language: requiredStringFor(value.language, "language", errorPrefix),
    advisor_profile: requiredStringFor(value.advisor_profile, "advisor_profile", errorPrefix),
    scope: parseInsightScope(value.scope),
    headline: requiredStringFor(value.headline, "headline", errorPrefix),
    executive_findings: requiredObjectList(
      value.executive_findings,
      "executive_findings",
      errorPrefix
    ).map(parseExecutiveFinding),
    business_signals: requiredObjectList(
      value.business_signals,
      "business_signals",
      errorPrefix
    ).map(parseBusinessSignal),
    action_plan: requiredObjectList(value.action_plan, "action_plan", errorPrefix).map(
      parseActionRecommendation
    ),
    evidence_refs: requiredObjectList(value.evidence_refs, "evidence_refs", errorPrefix).map(
      parseEvidenceReference
    ),
    confidence: parseBriefConfidence(value.confidence),
    data_gaps: requiredObjectList(value.data_gaps, "data_gaps", errorPrefix).map(
      parseDataGap
    ),
    generation_method: requiredStringFor(
      value.generation_method,
      "generation_method",
      errorPrefix
    ),
    created_at: requiredStringFor(value.created_at, "created_at", errorPrefix)
  };
}

function parseInsightScope(value: unknown): InsightScope {
  const errorPrefix = "insight_briefs_invalid_response";
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:scope_object_required`);
  }

  return {
    platform: requiredPlatform(value.platform, errorPrefix),
    source_object_type: requiredStringFor(
      value.source_object_type,
      "scope_source_object_type",
      errorPrefix
    ),
    source_object_id: requiredStringFor(
      value.source_object_id,
      "scope_source_object_id",
      errorPrefix
    ),
    source_url: requiredStringFor(value.source_url, "scope_source_url", errorPrefix),
    collection_run_ids: stringList(value.collection_run_ids),
    coverage_scope: requiredStringFor(
      value.coverage_scope,
      "scope_coverage_scope",
      errorPrefix
    ),
    coverage_confidence: requiredFiniteNumber(
      value.coverage_confidence,
      "scope_coverage_confidence",
      errorPrefix
    )
  };
}

function parseExecutiveFinding(value: Record<string, unknown>): ExecutiveFinding {
  const errorPrefix = "insight_briefs_invalid_response";
  return {
    finding_id: requiredStringFor(value.finding_id, "finding_id", errorPrefix),
    title: requiredStringFor(value.title, "title", errorPrefix),
    business_meaning: requiredStringFor(
      value.business_meaning,
      "business_meaning",
      errorPrefix
    ),
    priority: requiredStringFor(value.priority, "priority", errorPrefix),
    confidence_level: requiredStringFor(
      value.confidence_level,
      "confidence_level",
      errorPrefix
    ),
    evidence_ref_ids: stringList(value.evidence_ref_ids)
  };
}

function parseBusinessSignal(value: Record<string, unknown>): BusinessSignal {
  const errorPrefix = "insight_briefs_invalid_response";
  return {
    signal_id: requiredStringFor(value.signal_id, "signal_id", errorPrefix),
    signal_type: requiredStringFor(value.signal_type, "signal_type", errorPrefix),
    topic: requiredStringFor(value.topic, "topic", errorPrefix),
    aspect: requiredStringFor(value.aspect, "aspect", errorPrefix),
    customer_language: stringList(value.customer_language),
    business_impact: requiredStringFor(value.business_impact, "business_impact", errorPrefix),
    severity: requiredStringFor(value.severity, "severity", errorPrefix),
    priority: requiredStringFor(value.priority, "priority", errorPrefix),
    evidence_strength: requiredStringFor(
      value.evidence_strength,
      "evidence_strength",
      errorPrefix
    ),
    confidence_reason: requiredStringFor(
      value.confidence_reason,
      "confidence_reason",
      errorPrefix
    ),
    evidence_ref_ids: stringList(value.evidence_ref_ids),
    quality_flags: stringList(value.quality_flags)
  };
}

function parseActionRecommendation(
  value: Record<string, unknown>
): ActionRecommendation {
  const errorPrefix = "insight_briefs_invalid_response";
  return {
    action_id: requiredStringFor(value.action_id, "action_id", errorPrefix),
    action_type: requiredStringFor(value.action_type, "action_type", errorPrefix),
    title: requiredStringFor(value.title, "title", errorPrefix),
    recommendation: requiredStringFor(value.recommendation, "recommendation", errorPrefix),
    why_now: requiredStringFor(value.why_now, "why_now", errorPrefix),
    expected_metric: requiredStringFor(value.expected_metric, "expected_metric", errorPrefix),
    owner_role: requiredStringFor(value.owner_role, "owner_role", errorPrefix),
    priority: requiredStringFor(value.priority, "priority", errorPrefix),
    effort: requiredStringFor(value.effort, "effort", errorPrefix),
    evidence_ref_ids: stringList(value.evidence_ref_ids)
  };
}

function parseEvidenceReference(value: Record<string, unknown>): EvidenceReference {
  const errorPrefix = "insight_briefs_invalid_response";
  return {
    evidence_ref_id: requiredStringFor(value.evidence_ref_id, "evidence_ref_id", errorPrefix),
    voc_unit_id: requiredStringFor(value.voc_unit_id, "voc_unit_id", errorPrefix),
    platform: requiredPlatform(value.platform, errorPrefix),
    source_kind: requiredStringFor(value.source_kind, "source_kind", errorPrefix),
    source_object_id: requiredStringFor(value.source_object_id, "source_object_id", errorPrefix),
    quote: requiredStringFor(value.quote, "quote", errorPrefix),
    normalized_quote: optionalString(value.normalized_quote),
    rating: optionalNumber(value.rating),
    relation_edge_ids: stringList(value.relation_edge_ids),
    quality_flags: stringList(value.quality_flags),
    source_url: requiredStringFor(value.source_url, "source_url", errorPrefix)
  };
}

function parseBriefConfidence(value: unknown): BriefConfidence {
  const errorPrefix = "insight_briefs_invalid_response";
  if (!isRecord(value)) {
    throw new Error(`${errorPrefix}:confidence_object_required`);
  }

  return {
    level: requiredStringFor(value.level, "confidence_level", errorPrefix),
    reason: requiredStringFor(value.reason, "confidence_reason", errorPrefix),
    evidence_count: requiredFiniteIntegerFor(
      value.evidence_count,
      "confidence_evidence_count",
      errorPrefix
    ),
    source_diversity: requiredStringFor(
      value.source_diversity,
      "confidence_source_diversity",
      errorPrefix
    ),
    coverage_notes: stringList(value.coverage_notes)
  };
}

function parseDataGap(value: Record<string, unknown>): DataGap {
  const errorPrefix = "insight_briefs_invalid_response";
  return {
    gap_type: requiredStringFor(value.gap_type, "gap_type", errorPrefix),
    description: requiredStringFor(value.description, "description", errorPrefix),
    recommended_collection: requiredStringFor(
      value.recommended_collection,
      "recommended_collection",
      errorPrefix
    ),
    blocks_confidence: requiredBooleanFor(
      value.blocks_confidence,
      "blocks_confidence",
      errorPrefix
    )
  };
}

function requiredPlatform(value: unknown, errorPrefix = "voc_units_invalid_response"): VocPlatform {
  if (value === "amazon" || value === "reddit" || value === "instagram") {
    return value;
  }

  throw new Error(`${errorPrefix}:item_platform_required`);
}

function requiredString(value: unknown, field: string): string {
  return requiredStringFor(value, field, "voc_units_invalid_response");
}

function requiredStringFor(value: unknown, field: string, errorPrefix: string): string {
  if (typeof value === "string") {
    return value;
  }

  throw new Error(`${errorPrefix}:${field}_required`);
}

function requiredCollectionTaskStatus(value: unknown): CollectionTaskStatus {
  if (
    value === "pending" ||
    value === "running" ||
    value === "retry_scheduled" ||
    value === "completed" ||
    value === "failed"
  ) {
    return value;
  }

  throw new Error("collection_tasks_invalid_response:status_required");
}

function requiredCaptureCapabilityMode(value: unknown): CaptureCapabilityMode {
  if (value === "extension" || value === "server" || value === "fixture") {
    return value;
  }

  throw new Error("capture_capabilities_invalid_response:mode_required");
}

function requiredCaptureCapabilityStatus(value: unknown): CaptureCapabilityStatus {
  if (
    value === "ready" ||
    value === "authorization_required" ||
    value === "fixture_only" ||
    value === "credential_missing" ||
    value === "live_read_blocked" ||
    value === "task_authorization_required"
  ) {
    return value;
  }

  throw new Error("capture_capabilities_invalid_response:status_required");
}

function requiredInstagramGraphLiveReadPreflightStatus(
  value: unknown
): InstagramGraphLiveReadPreflightStatus {
  if (
    value === "ready" ||
    value === "credential_missing" ||
    value === "live_read_blocked" ||
    value === "task_authorization_required"
  ) {
    return value;
  }

  throw new Error("instagram_graph_live_read_preflight_invalid_response:status_required");
}

function requiredPlatformSettingSource(
  value: unknown,
  errorPrefix: string
): PlatformSettingSource {
  if (value === "default" || value === "stored") {
    return value;
  }

  throw new Error(`${errorPrefix}:source_required`);
}

function requiredAnalysisArtifactType(
  value: unknown,
  errorPrefix: string
): AnalysisArtifactType {
  if (
    value === "relation_edge" ||
    value === "enriched_voc_signal" ||
    value === "strategy_note" ||
    value === "insight_brief"
  ) {
    return value;
  }
  throw new Error(`${errorPrefix}:artifact_type_required`);
}

function optionalString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function optionalBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function requiredFiniteNumber(
  value: unknown,
  field: string,
  errorPrefix = "voc_units_invalid_response"
): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  throw new Error(`${errorPrefix}:${field}_required`);
}

function requiredFiniteInteger(value: unknown, field: string): number {
  return requiredFiniteIntegerFor(value, field, "strategy_notes_invalid_response");
}

function requiredFiniteIntegerFor(value: unknown, field: string, errorPrefix: string): number {
  if (typeof value === "number" && Number.isSafeInteger(value)) {
    return value;
  }

  throw new Error(`${errorPrefix}:${field}_required`);
}

function requiredNonNegativeIntegerFor(
  value: unknown,
  field: string,
  errorPrefix: string
): number {
  const parsed = requiredFiniteIntegerFor(value, field, errorPrefix);
  if (parsed < 0) {
    throw new Error(`${errorPrefix}:${field}_required`);
  }
  return parsed;
}

function requiredBooleanFor(value: unknown, field: string, errorPrefix: string): boolean {
  if (typeof value === "boolean") {
    return value;
  }

  throw new Error(`${errorPrefix}:${field}_required`);
}

function optionalNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string");
}

function requiredStringListFor(
  value: unknown,
  field: string,
  errorPrefix: string
): string[] {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new Error(`${errorPrefix}:${field}_array_required`);
  }
  return value;
}

function jsonObject(value: unknown): Record<string, JsonValue> {
  if (!isRecord(value)) {
    return {};
  }

  const output: Record<string, JsonValue> = {};
  for (const [key, item] of Object.entries(value)) {
    if (isJsonValue(item)) {
      output[key] = item;
    }
  }
  return output;
}

function requiredJsonObjectFor(
  value: unknown,
  field: string,
  errorPrefix: string
): Record<string, JsonValue> {
  if (!isRecord(value) || !Object.values(value).every(isJsonValue)) {
    throw new Error(`${errorPrefix}:${field}_object_required`);
  }
  return value as Record<string, JsonValue>;
}

function jsonList(value: unknown): JsonValue[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(isJsonValue);
}

function requiredObjectList(
  value: unknown,
  field: string,
  errorPrefix: string
): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    throw new Error(`${errorPrefix}:${field}_array_required`);
  }
  if (!value.every(isRecord)) {
    throw new Error(`${errorPrefix}:${field}_object_required`);
  }
  return value;
}

function isJsonValue(value: unknown): value is JsonValue {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  ) {
    return true;
  }

  if (Array.isArray(value)) {
    return value.every(isJsonValue);
  }

  if (isRecord(value)) {
    return Object.values(value).every(isJsonValue);
  }

  return false;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
